#!/usr/bin/env python3
"""Resolve CDeviceConfig's runtime performance-profile pointer table."""
from __future__ import annotations
import sys
from pathlib import Path
from elftools.elf.elffile import ELFFile

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: inspect_performance_profile_table.py libABBS.so report.txt")
    elf_path, out_path = map(Path, sys.argv[1:])
    lines = []
    with elf_path.open("rb") as f:
        elf = ELFFile(f)
        def vread(va, size):
            for sec in elf.iter_sections():
                if sec.header.sh_type == "SHT_NOBITS":
                    continue
                start = int(sec.header.sh_addr)
                data = sec.data()
                if start <= va and va + size <= start + len(data):
                    return data[va - start:va - start + size]
            return b""
        reloc = {}
        for sec in elf.iter_sections():
            if sec.header.sh_type not in ("SHT_RELA", "SHT_REL"):
                continue
            for item in sec.iter_relocations():
                ent = item.entry
                reloc[int(ent.r_offset)] = ent
        table = 0xcb07c0
        lines.append(f"ELF={elf_path.name} machine={elf.header['e_machine']} table=0x{table:x}")
        for index in range(8):
            slot = table + index * 8
            entry = reloc.get(slot)
            ptr = None
            if entry is not None:
                addend = entry.get("r_addend")
                if addend is not None:
                    ptr = int(addend)
            if ptr is None:
                raw_ptr = vread(slot, 8)
                if len(raw_ptr) == 8:
                    ptr = int.from_bytes(raw_ptr, "little")
            if not ptr:
                lines.append(f"PROFILE[{index}] slot=0x{slot:x} unresolved")
                continue
            raw = vread(ptr, 512)
            name = raw.split(b"\\0", 1)[0].decode("utf-8", "replace") if raw else "<unmapped>"
            lines.append(f"PROFILE[{index}] slot=0x{slot:x} ptr=0x{ptr:x} name={name}")
            if not raw or b"\\0" not in raw:
                break
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print("\\n".join(lines))

if __name__ == "__main__":
    main()