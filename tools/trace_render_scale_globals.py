#!/usr/bin/env python3
"""Trace relocation-backed render-scale globals and the ScaleRenderTargetRes data table."""
from __future__ import annotations
import io, sys, zipfile, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM, CS_OP_MEM, CS_OP_REG

apk, out = map(Path, sys.argv[1:3])
with zipfile.ZipFile(apk) as z:
    raw = z.read("lib/arm64-v8a/libABBS.so")
elf = ELFFile(io.BytesIO(raw))
targets = {
    0xd418c8: "m_fScale3D_X", 0xd418d0: "m_fScale3D_Y",
    0xd418d8: "m_fDynResMin", 0xd418e0: "m_iShadowMapSize",
    0x483f80: "ScaleRenderTargetRes",
}
lines = ["Render-scale relocation and data-structure trace",
         f"ELF machine={elf['e_machine']} class={elf.elfclass}", ""]
# Relocations reveal the exact symbol/addend used to initialize pointer slots.
lines.append("## Relocations involving scale globals or the render-scale callback")
relocation_slots = {}
for sec in elf.iter_sections():
    if not isinstance(sec, RelocationSection):
        continue
    symtab = elf.get_section(sec['sh_link'])
    for rel in sec.iter_relocations():
        off = int(rel['r_offset'])
        symidx = int(rel['r_info_sym'])
        sym = symtab.get_symbol(symidx) if symidx < symtab.num_symbols() else None
        name = sym.name if sym else "<no-symbol>"
        sval = int(sym['st_value']) if sym else 0
        addend = int(rel['r_addend']) if rel.is_RELA() else None
        related = any(sval == t or (addend is not None and (sval + addend) == t) for t in targets)
        near_slots = 0xe5f70 <= off <= 0xe6000
        if related or near_slots:
            if related:
                relocation_slots[off] = str(name) + " -> " + str(targets.get(sval + (addend or 0), "scale-global"))
            typ = rel['r_info_type']
            lines.append(f"{sec.name}: place={off:#x} type={typ} symbol={name!r} sym_value={sval:#x} addend={addend!r} resolved={(sval + addend if addend is not None else sval):#x}")
# Decode the packed object/table around the unaligned callback pointer.
ro = elf.get_section_by_name(".rodata")
if ro:
    va, data = int(ro['sh_addr']), ro.data()
    start_va, end_va = 0x117e00, 0x117ec0
    if va <= start_va < va + len(data):
        start, end = start_va-va, min(end_va-va, len(data))
        blob = data[start:end]
        lines += ["", "## .rodata packed table at 0x117e00",
                  "offset | u32 | float | u64"]
        for p in range(0, len(blob)-7, 4):
            u32 = struct.unpack_from("<I", blob, p)[0]
            f32 = struct.unpack_from("<f", blob, p)[0]
            u64 = struct.unpack_from("<Q", blob, p)[0] if p % 8 == 0 and p+8 <= len(blob) else 0
            lines.append(f"{start_va+p:#x} | {u32:#010x} | {f32:.7g} | {u64:#018x}")
# Find code that materializes addresses inside the table's page and then accesses them.
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN); md.detail = True
textsec = elf.get_section_by_name(".text")
base, code = int(textsec['sh_addr']), textsec.data()
insns = list(md.disasm(code, base))
lines += ["", "## Code references to relocation slots (pointer indirection)"]
for i, ins in enumerate(insns):
    if ins.mnemonic != "adrp" or len(ins.operands) < 2:
        continue
    if ins.operands[0].type != CS_OP_REG or ins.operands[1].type != CS_OP_IMM:
        continue
    reg = ins.reg_name(ins.operands[0].reg)
    page = int(ins.operands[1].imm)
    for nxt in insns[i+1:i+12]:
        if nxt.mnemonic in ("bl", "blr", "b", "ret"):
            break
        for op in nxt.operands:
            if op.type == CS_OP_MEM and op.mem.base and nxt.reg_name(op.mem.base) == reg:
                ea = page + int(op.mem.disp)
                if ea in relocation_slots:
                    lines.append(f"slot {ea:#x} ({relocation_slots[ea]}): ADRP {ins.address:#x}; {nxt.address:#x}: {nxt.mnemonic} {nxt.op_str}")
lines += ["", "## Code references to .rodata page 0x117000"]
for i, ins in enumerate(insns):
    if ins.mnemonic != "adrp" or len(ins.operands) < 2:
        continue
    if ins.operands[0].type != CS_OP_REG or ins.operands[1].type != CS_OP_IMM:
        continue
    reg = ins.reg_name(ins.operands[0].reg)
    page = int(ins.operands[1].imm)
    if page != 0x117000:
        continue
    seq = []
    for nxt in insns[i+1:i+10]:
        if nxt.mnemonic in ("bl", "blr", "b", "ret"):
            break
        seq.append(f"{nxt.address:#x}: {nxt.mnemonic} {nxt.op_str}")
        for op in nxt.operands:
            if op.type == CS_OP_MEM and op.mem.base and nxt.reg_name(op.mem.base) == reg:
                ea = page + int(op.mem.disp)
                if 0x117e00 <= ea <= 0x117ec0:
                    lines.append(f"ADRP {ins.address:#x} -> {ea:#x} via {reg}; " + " | ".join(seq))
                    break

# Also list every instruction that addresses the GOT/data pages holding the
# relocation slots. The earlier narrow scan only matched a single ADRP+memory
# pair and could miss compiler-generated address materialization sequences.
lines += ["", "## Broad code references to relocation/GOT pages"]
interesting_pages = {0xcee000, 0xcef000, 0xd41000, 0xd418000, 0x117000}
for i, ins in enumerate(insns):
    if ins.mnemonic != "adrp" or len(ins.operands) < 2:
        continue
    if ins.operands[0].type != CS_OP_REG or ins.operands[1].type != CS_OP_IMM:
        continue
    reg = ins.reg_name(ins.operands[0].reg)
    page = int(ins.operands[1].imm)
    if page not in interesting_pages:
        continue
    seq = []
    for nxt in insns[i+1:i+16]:
        seq.append(f"{nxt.address:#x}: {nxt.mnemonic} {nxt.op_str}")
        if nxt.mnemonic in ("bl", "blr", "b", "ret"):
            break
    lines.append(f"ADRP {ins.address:#x} page={page:#x} reg={reg}: " + " | ".join(seq))
# Resolve which ELF section contains each relocation place and the target global.
lines += ["", "## Relocation slot section mapping"]
for slot, desc in sorted(relocation_slots.items()):
    owner = next((s for s in elf.iter_sections()
                  if int(s['sh_addr']) <= slot < int(s['sh_addr']) + int(s['sh_size'])), None)
    lines.append(f"{slot:#x}: section={owner.name if owner else '<unmapped>'} {desc}")

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {out}")
