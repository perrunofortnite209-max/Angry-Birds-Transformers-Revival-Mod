#!/usr/bin/env python3
"""Focused read-only ARM64 disassembly for particle manager and VFX limit paths."""
from __future__ import annotations
import io, re, sys, zipfile
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM

apk, out = map(Path, sys.argv[1:3])
with zipfile.ZipFile(apk) as z:
    raw = z.read("lib/arm64-v8a/libABBS.so")
elf = ELFFile(io.BytesIO(raw))
symtab = elf.get_section_by_name(".symtab")
symbols = []
if symtab:
    for sym in symtab.iter_symbols():
        name = sym.name
        start, size = int(sym["st_value"]), int(sym["st_size"])
        if start and size and ("CParticleEffectManager" in name or
            "CExplosionManager" in name or "ParticleEffectInstance" in name):
            symbols.append((start, size, name))
symbols.sort()
textsec = elf.get_section_by_name(".text")
base, code = int(textsec["sh_addr"]), textsec.data()
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.detail = True
insns = list(md.disasm(code, base))
by_addr = {a:(s,n) for a,s,n in symbols}
lines = ["Focused particle/VFX native trace (read-only)", "APK: original 2.42.0; ABI: arm64-v8a", ""]
lines.append("## Relevant functions and disassembly")
for start, size, name in symbols:
    if not any(k in name for k in ("CParticleEffectManager", "CExplosionManager")):
        continue
    lines.append(f"\n### {name} [{start:#x}-{start+size:#x}] size={size:#x}")
    for ins in md.disasm(code[start-base:start-base+size], start):
        lines.append(f"{ins.address:08x}: {ins.mnemonic:<8} {ins.op_str}")
lines += ["", "## Direct callers of particle manager functions"]
manager = {a:(s,n) for a,s,n in symbols if "CParticleEffectManager" in n}
for ins in insns:
    if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == CS_OP_IMM:
        target = int(ins.operands[0].imm)
        if target in manager:
            size, name = manager[target]
            owner = next((n for a,s,n in symbols if a <= ins.address < a+s), "<unlabelled caller>")
            lines.append(f"{ins.address:#x} -> {target:#x} {name}; caller={owner}")
lines += ["", "## VFX-related native strings"]
for sec in elf.iter_sections():
    if sec.name not in (".rodata", ".data.rel.ro"):
        continue
    for m in re.finditer(rb"[ -~]{4,180}", sec.data()):
        value = m.group(0)
        low = value.lower()
        if any(k in low for k in (b"vfx", b"maxparticles", b"maxemitters",
            b"gemexplosion", b"particlesdisabled", b"effectsize",
            b"explosionsize", b"pigexplosion", b"emitter", b"softparticle")):
            lines.append(f"{int(sec['sh_addr'])+m.start():#x}: {value.decode('ascii','replace')}")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines)+"\n", encoding="utf-8")
print(f"Wrote {out}; selected_symbols={len(symbols)}")

# Analysis entrypoint: invoked by graphics-config-native-analysis.yml.
