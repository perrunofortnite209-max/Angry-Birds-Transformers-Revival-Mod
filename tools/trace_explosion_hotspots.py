#!/usr/bin/env python3
"""Static trace of explosion, particle and impact code paths in the arm64 game engine."""
from __future__ import annotations
import io, re, sys, zipfile
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, CS_OP_IMM

apk, out = map(Path, sys.argv[1:3])
with zipfile.ZipFile(apk) as z:
    raw = z.read("lib/arm64-v8a/libABBS.so")
    terms = (b"explosion", b"particle", b"emitter", b"debris", b"smoke",
             b"fire", b"blast", b"impact", b"destruct", b"projectile",
             b"shockwave", b"fragment", b"effect")
    lines = ["Explosion / particle hotspot static trace", "Scope: original arm64 engine and packaged assets", ""]
    lines.append("## Packaged resources mentioning effects")
    hits = 0
    for info in z.infolist():
        if info.is_dir() or info.file_size > 32 * 1024 * 1024:
            continue
        try:
            payload = z.read(info)
        except Exception:
            continue
        found = [t.decode() for t in terms if t in payload.lower()]
        if found:
            lines.append(f"{info.filename} ({info.file_size} bytes): {', '.join(found)}")
            hits += 1
            if hits >= 150:
                lines.append("... resource listing capped at 150 matches")
                break

elf = ELFFile(io.BytesIO(raw))
symtab = elf.get_section_by_name(".symtab")
symbols = []
if symtab:
    for sym in symtab.iter_symbols():
        name = sym.name
        start, size = int(sym["st_value"]), int(sym["st_size"])
        if start and size and any(t.decode() in name.lower() for t in terms):
            symbols.append((start, size, name))
symbols.sort()
lines += ["", "## Native symbols matching explosion / particle / impact terminology"]
for start, size, name in symbols[:250]:
    lines.append(f"{start:#x} size={size:#x} {name}")
if len(symbols) > 250:
    lines.append(f"... {len(symbols)-250} additional symbols omitted")

textsec = elf.get_section_by_name(".text")
base, code = int(textsec["sh_addr"]), textsec.data()
md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.detail = True
insns = list(md.disasm(code, base))
targets = {start for start, size, name in symbols}
callers = []
for ins in insns:
    if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == CS_OP_IMM:
        target = int(ins.operands[0].imm)
        if target in targets:
            owner = next(((s, e, n) for s, e, n in
                          ((a, a+b, c) for a,b,c in symbols) if s <= ins.address < e), None)
            callers.append((target, ins.address, owner[2] if owner else "<caller symbol unavailable>"))
lines += ["", "## Direct BL callers of matching native functions"]
for target, caller, owner in callers[:500]:
    name = next((n for s, size, n in symbols if s == target), "<unknown>")
    lines.append(f"call {caller:#x} -> {target:#x} {name}; caller={owner}")
if len(callers) > 500:
    lines.append(f"... {len(callers)-500} additional calls omitted")

lines += ["", "## Disassembly of matching native functions"]
for start, size, name in symbols[:80]:
    end = min(start + size, start + 0x500)
    lines.append(f"\n### {name} [{start:#x}-{end:#x}]")
    for ins in md.disasm(code[start-base:end-base], start):
        lines.append(f"{ins.address:08x}: {ins.mnemonic:<8} {ins.op_str}")

# Scan the native read-only data for relevant labels and effect-system names.
for sec in elf.iter_sections():
    if sec.name not in (".rodata", ".data.rel.ro"):
        continue
    data = sec.data()
    lines += ["", f"## Strings in {sec.name} matching effect terms"]
    for m in re.finditer(rb"[ -~]{5,160}", data):
        value = m.group(0)
        low = value.lower()
        if any(t in low for t in terms):
            lines.append(f"{int(sec['sh_addr'])+m.start():#x}: {value.decode('ascii','replace')}")
            if len(lines) > 20000:
                break

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out}; matching_symbols={len(symbols)}; direct_calls={len(callers)}")
