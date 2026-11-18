#!/usr/bin/env python3
"""Read-only ARM64 disassembly of XGS frame/render pass functions."""
from __future__ import annotations
import io, re, sys, zipfile
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM

APK = Path(sys.argv[1])
OUT = Path(sys.argv[2])
EXPECTED = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
import hashlib
digest = hashlib.sha256(APK.read_bytes()).hexdigest()
if digest != EXPECTED:
    raise SystemExit(f"Wrong APK SHA-256: {digest}")

TARGETS = [
    ("CApp::DoRender", re.compile(r"_ZN4CApp8DoRenderEv$")),
    ("CGame::RenderFrame", re.compile(r"_ZN5CGame11RenderFrameEv$")),
    ("CRenderManager::RenderFrame", re.compile(r"_ZN14CRenderManager11RenderFrameEv$")),
    ("CRenderManager::PrepareFrame", re.compile(r"_ZN14CRenderManager12PrepareFrameEv$")),
    ("CRenderManager::RenderShadowMap", re.compile(r"_ZN14CRenderManager15RenderShadowMapEv$")),
    ("CRenderManager::RenderReflectionMap", re.compile(r"_ZN14CRenderManager19RenderReflectionMapEv$")),
    ("CRenderManager::RenderDepthPass", re.compile(r"_ZN14CRenderManager15RenderDepthPassEv$")),
    ("CRenderManager::RenderPostProcess", re.compile(r"_ZN14CRenderManager17RenderPostProcessEv$")),
    ("CXGSRenderDeviceOGL::PresentScene", re.compile(r"_ZN19CXGSRenderDeviceOGL12PresentSceneEP11IXGSDisplayi$")),
    ("CParticleEffectManager::PrepareFrame", re.compile(r"_ZN22CParticleEffectManager12PrepareFrameEv$")),
    ("CEnvObject::PrepareFrame", re.compile(r"_ZN11CEnvObject12PrepareFrameEv$")),
    ("C2DBatchControllerByMaterial::OnEndFrame", re.compile(r"_ZN28C2DBatchControllerByMaterial10OnEndFrameEv$")),
]
with zipfile.ZipFile(APK) as z:
    elf_bytes = z.read("lib/arm64-v8a/libABBS.so")
elf = ELFFile(io.BytesIO(elf_bytes))
textsec = elf.get_section_by_name(".text")
if textsec is None:
    raise SystemExit("No .text section")
base = int(textsec.header.sh_addr)
text = textsec.data()
symbols = {}
for sec in elf.iter_sections():
    if sec.header.sh_type not in ("SHT_SYMTAB", "SHT_DYNSYM"):
        continue
    for sym in sec.iter_symbols():
        if sym.name and int(sym.entry.st_size):
            symbols.setdefault(int(sym.entry.st_value), (sym.name, int(sym.entry.st_size)))
by_addr = {a:n for a,(n,s) in symbols.items()}
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.detail = True
out = [
    "# XGS ARM64 render-pass static inspection",
    "",
    f"- APK SHA-256 verified: {digest}",
    "- Read-only static disassembly; this report does not measure runtime cost.",
    "- Direct BL calls are resolved where a named symbol exists; BLR calls are indirect/vtable calls.",
    "",
]
for label, rx in TARGETS:
    matches = [(a,n,s) for a,(n,s) in symbols.items() if rx.search(n)]
    out += [f"## {label}", ""]
    if len(matches) != 1:
        out.append(f"Expected one named function, found {len(matches)}: {[(hex(a),n,s) for a,n,s in matches]}")
        out.append("")
        continue
    addr,name,size = matches[0]
    if not (base <= addr < base + len(text)):
        out.append(f"Address {addr:#x} outside .text")
        continue
    code = text[addr-base:addr-base+size]
    insns = list(md.disasm(code, addr))
    calls = []
    back_edges = []
    for ins in insns:
        if ins.mnemonic in ("bl","b") and ins.operands and ins.operands[0].type == CS_OP_IMM:
            dest = int(ins.operands[0].imm)
            if ins.mnemonic == "bl":
                calls.append((ins.address,dest,by_addr.get(dest,"<unnamed or indirect>")))
            elif dest < ins.address:
                back_edges.append((ins.address,dest))
    out.append(f"- Symbol: `{name}`")
    out.append(f"- Address / size: `{addr:#x}` / `{size:#x}` ({len(insns)} instructions)")
    out.append(f"- Direct BL calls: {len(calls)}; backward B edges: {len(back_edges)}")
    if back_edges:
        out.append("- Backward branch targets: " + ", ".join(f"`{a:#x}→{b:#x}`" for a,b in back_edges))
    out.append("")
    out.append("**Call targets**")
    if calls:
        out.extend(f"- `{site:#x}` → `{target:#x}` `{callee}`" for site,target,callee in calls)
    else:
        out.append("- None identified")
    out.append("")
    out.append("**Disassembly**")
    out.append("")
    out.append("```asm")
    for ins in insns:
        comment = ""
        if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == CS_OP_IMM:
            dest = int(ins.operands[0].imm)
            target = by_addr.get(dest)
            if target:
                comment = f" ; {target}"
        out.append(f"{ins.address:08x}: {ins.mnemonic:8} {ins.op_str}{comment}")
    out.append("```")
    out.append("")
out += [
    "## Interpretation guardrails",
    "",
    "- A static call sequence identifies candidate work, not the time spent in each pass.",
    "- A render pass must not be disabled based only on its name or presence.",
    "- The Perfetto capture shows high CPU occupancy in GLThread/onDrawFrame, but has no native sampled stacks or GPU frame timeline.",
    "- Any optimization must preserve scene correctness and be A/B measured in the same gameplay scene.",
]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
