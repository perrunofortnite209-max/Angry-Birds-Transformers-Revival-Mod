#!/usr/bin/env python3
"""Trace AArch64 code references to CRenderManager scale-related globals."""
from __future__ import annotations
import io, sys, zipfile, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM, CS_OP_MEM, CS_OP_REG

apk, out = map(Path, sys.argv[1:3])
with zipfile.ZipFile(apk) as z:
    raw = z.read("lib/arm64-v8a/libABBS.so")
elf = ELFFile(io.BytesIO(raw))
targets = {
    0xd418c8: "m_fScale3D_X",
    0xd418d0: "m_fScale3D_Y",
    0xd418d8: "m_fDynResMin",
    0xd418e0: "m_iShadowMapSize",
}
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.detail = True
textsec = elf.get_section_by_name(".text")
base, code = int(textsec.header.sh_addr), textsec.data()
insns = list(md.disasm(code, base))
lines = ["AArch64 references to render-scale globals (static/read-only)", f".text VA={base:#x} size={len(code):#x}", ""]
# ADRP establishes a 4-KiB page; follow nearby instructions that use that register.
for i, ins in enumerate(insns):
    if ins.mnemonic != "adrp" or len(ins.operands) < 2:
        continue
    regop, immop = ins.operands[0], ins.operands[1]
    if regop.type != CS_OP_REG or immop.type != CS_OP_IMM:
        continue
    reg = ins.reg_name(regop.reg)
    page = int(immop.imm)
    for nxt in insns[i+1:i+9]:
        if nxt.mnemonic in ("bl", "blr", "b", "ret"):
            break
        for op in nxt.operands:
            if op.type != CS_OP_MEM or op.mem.base == 0:
                continue
            if nxt.reg_name(op.mem.base) != reg:
                continue
            effective = page + int(op.mem.disp)
            for addr, name in targets.items():
                if effective == addr:
                    lines.append(f"{ins.address:#x}: {ins.mnemonic} {ins.op_str}; {nxt.address:#x}: {nxt.mnemonic} {nxt.op_str} => {name} [{addr:#x}]")
# Search data sections for pointers to scale helpers and globals.
lines.append("\n## Data pointer hits")
needles = {0x483f80:"ScaleRenderTargetRes", **targets}
for sec in elf.iter_sections():
    if not (int(sec.header.sh_flags) & 0x2):
        continue
    data, va = sec.data(), int(sec.header.sh_addr)
    for addr, name in needles.items():
        needle = struct.pack("<Q", addr)
        pos = 0
        while True:
            off = data.find(needle, pos)
            if off < 0: break
            lines.append(f"{sec.name}+{off:#x} VA={va+off:#x} -> {name} ({addr:#x})")
            pos = off + 1
# Include bytes and decoded qwords around the known function-pointer table.
lines.append("\n## .rodata around ScaleRenderTargetRes pointer (VA 0x117e4e)")
for sec in elf.iter_sections():
    va = int(sec.header.sh_addr)
    if va <= 0x117e4e < va + int(sec.header.sh_size):
        off = 0x117e4e - va
        start, end = max(0, off-64), min(len(sec.data()), off+96)
        blob = sec.data()[start:end]
        lines.append(f"section={sec.name} range={va+start:#x}-{va+end:#x}")
        lines.append(blob.hex())
        for p in range(0, len(blob)-7, 8):
            val = struct.unpack_from("<Q", blob, p)[0]
            if val:
                lines.append(f"{va+start+p:#x}: {val:#x}")
        break
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines)+"\n", encoding="utf-8")
print(f"Wrote {out}")
