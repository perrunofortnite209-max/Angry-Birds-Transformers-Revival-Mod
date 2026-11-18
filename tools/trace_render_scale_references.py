#!/usr/bin/env python3
"""Read-only trace of CRenderManager scale helper references and vtable slots."""
from __future__ import annotations
import io, sys, zipfile, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM

apk, out = map(Path, sys.argv[1:3])
with zipfile.ZipFile(apk) as z:
    elf_bytes = z.read("lib/arm64-v8a/libABBS.so")
elf = ELFFile(io.BytesIO(elf_bytes))
textsec = elf.get_section_by_name(".text")
if textsec is None:
    raise SystemExit("No .text section")
text_base = int(textsec.header.sh_addr)
text = textsec.data()
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.detail = True

targets = {
    0x483f80: "ScaleRenderTargetRes",
    0x484d34: "UpdateDynamicRes",
    0x48354c: "CreateMainSceneRT",
    0x4832e4: "CreateVolatileResources",
    0x4837b0: "GetScaledScreenRes",
    0x6e4a90: "ProcessFrame_UpdateDynamicRes_call",
}
symbols = {}
for sec in elf.iter_sections():
    if sec.header.sh_type not in ("SHT_SYMTAB", "SHT_DYNSYM"):
        continue
    for sym in sec.iter_symbols():
        if sym.name and int(sym.entry.st_size):
            symbols[int(sym.entry.st_value)] = (sym.name, int(sym.entry.st_size))

lines = [
    "CRenderManager render-scale reference trace (static, read-only)",
    f"ELF machine={elf.header['e_machine']} class={elf.elfclass}",
    "",
    "## Exact functions",
]
for addr, label in targets.items():
    if addr not in (0x483f80, 0x484d34, 0x48354c, 0x4832e4, 0x4837b0):
        continue
    sym = symbols.get(addr)
    lines.append(f"\n### {label} @ {addr:#x} symbol={sym}")
    size = sym[1] if sym else 0x100
    if not (text_base <= addr < text_base + len(text)):
        lines.append("outside .text")
        continue
    code = text[addr-text_base:addr-text_base+min(size, 0x500)]
    for ins in md.disasm(code, addr):
        comment = ""
        if ins.mnemonic in ("bl", "b") and ins.operands and ins.operands[0].type == CS_OP_IMM:
            dest = int(ins.operands[0].imm)
            if dest in symbols:
                comment = " ; " + symbols[dest][0]
        lines.append(f"{ins.address:08x}: {ins.mnemonic:8} {ins.op_str}{comment}")

lines.append("\n## Direct BL callers")
for ins in md.disasm(text, text_base):
    if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == CS_OP_IMM:
        dest = int(ins.operands[0].imm)
        if dest in targets:
            owner_addr = max((a for a in symbols if a <= ins.address), default=None)
            owner = symbols.get(owner_addr, ("<unknown>", 0))[0]
            lines.append(f"{ins.address:#x} -> {dest:#x} {targets[dest]} in {owner}")

lines.append("\n## Raw pointer references to target function addresses")
for sec in elf.iter_sections():
    if not (int(sec.header.sh_flags) & 0x2):
        continue
    data = sec.data()
    base = int(sec.header.sh_addr)
    for addr, label in targets.items():
        if addr not in (0x483f80, 0x484d34, 0x48354c, 0x4832e4, 0x4837b0):
            continue
        needle = struct.pack("<Q", addr)
        pos = 0
        while True:
            off = data.find(needle, pos)
            if off < 0:
                break
            lines.append(f"{sec.name}+{off:#x} VA={base+off:#x} -> {label} ({addr:#x})")
            pos = off + 1

lines.append("\n## CRenderManager and DeviceConfig vtable-like symbols")
for addr, (name, size) in sorted(symbols.items()):
    if any(x in name for x in ("vtable", "VTT", "CRenderManager", "CDeviceConfig")):
        lines.append(f"{addr:#x} size={size:#x} {name}")

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {out} ({len(lines)} lines)")
