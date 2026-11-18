#!/usr/bin/env python3
"""Inspect the native profile pointer table used by CDeviceConfig."""
import sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
def main():
    if len(sys.argv) != 3: raise SystemExit("usage: script libABBS.so output.txt")
    elf_path, out_path = map(Path, sys.argv[1:])
    lines=[]
    with elf_path.open("rb") as f:
        elf=ELFFile(f)
        def vread(va,n):
            for sec in elf.iter_sections():
                if sec.header.sh_type == "SHT_NOBITS": continue
                start=int(sec.header.sh_addr); data=sec.data()
                if start <= va and va+n <= start+len(data): return data[va-start:va-start+n]
            return b""
        relocs={}
        for sec in elf.iter_sections():
            if sec.header.sh_type not in ("SHT_RELA","SHT_REL"): continue
            for rel in sec.iter_relocations(): relocs[int(rel.entry.r_offset)]=rel.entry
        table=0xcb07c0
        lines.append(f"ELF={elf_path.name} machine={elf.header['e_machine']} table=0x{table:x}")
        for i in range(8):
            slot=table+i*8; ent=relocs.get(slot); ptr=None
            if ent is not None and ent.get("r_addend") is not None: ptr=int(ent.get("r_addend"))
            raw_slot=vread(slot,8)
            if ptr is None and len(raw_slot)==8: ptr=int.from_bytes(raw_slot,"little")
            if not ptr: lines.append(f"PROFILE[{i}] slot=0x{slot:x} raw={raw_slot.hex()} unresolved"); continue
            raw=vread(ptr,128)
            name=raw.split(bytes([0]),1)[0].decode("utf-8","replace") if raw else "<unmapped>"
            lines.append(f"PROFILE[{i}] slot=0x{slot:x} raw={raw_slot.hex()} ptr=0x{ptr:x} name={name}")
    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines))
if __name__ == "__main__": main()