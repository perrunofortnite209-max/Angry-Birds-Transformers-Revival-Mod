#!/usr/bin/env python3
"""Inspect XGS native UI/FPS symbols and disassemble relevant AArch64 functions."""
from __future__ import annotations
import argparse, re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

NEEDLES = (
    "FeatureConfig", "ToggleFeature", "RateGameButtonTapped",
    "ShowSettingsScreen", "dismissFeatureConfigScreen", "TogglePage",
    "GetDesiredFramerate", "LimitFPSWithSleep", "DoPresent",
    "LowBatteryFPSCap", "TARGET_60_FPS", "SettingsScreen",
)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("elf",type=Path)
    ap.add_argument("output",type=Path)
    args=ap.parse_args()
    lines=[]
    with args.elf.open("rb") as f:
        elf=ELFFile(f)
        lines.append(f"ELF class={elf.elfclass} machine={elf.header['e_machine']} endian={elf.little_endian}")
        symbols=[]
        for sec in elf.iter_sections():
            if sec.header.sh_type in ("SHT_SYMTAB","SHT_DYNSYM"):
                for sym in sec.iter_symbols():
                    name=sym.name
                    if name and any(n.lower() in name.lower() for n in NEEDLES):
                        symbols.append((int(sym.entry.st_value),int(sym.entry.st_size),name,sym.entry.st_info.type))
        seen=set()
        for addr,size,name,typ in sorted(symbols):
            key=(addr,name)
            if key in seen: continue
            seen.add(key)
            lines.append(f"SYMBOL 0x{addr:x} size=0x{size:x} type={typ} {name}")
        textsec=elf.get_section_by_name(".text")
        if textsec:
            md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
            text= textsec.data()
            base=int(textsec.header.sh_addr)
            funcsyms=[x for x in symbols if x[0]>=base and x[0]<base+len(text) and x[2]]
            for addr,size,name,typ in sorted(funcsyms):
                if size<=0: continue
                off=addr-base
                chunk=text[off:off+min(size,0x1800)]
                lines.append(f"\nDISASSEMBLY {name} @0x{addr:x} size=0x{size:x}")
                for ins in md.disasm(chunk,addr):
                    lines.append(f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}")
        # Locate relevant strings in file offsets for later xref work.
        blob=args.elf.read_bytes()
        for m in re.finditer(rb"[ -~]{5,}",blob):
            s=m.group().decode("ascii","replace")
            if any(n.lower() in s.lower() for n in NEEDLES) or "XMLPAK:Global/FeatureConfig.xml" in s:
                lines.append(f"STRING file+0x{m.start():x}: {s[:240]}")
    args.output.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {args.output}")

if __name__=="__main__": main()
