#!/usr/bin/env python3
"""Read-only XGS performance-path inventory for the original APK's ARM64 library."""
from __future__ import annotations
import argparse, re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

PATTERNS = re.compile(
    r"render|present|swap|frame|fps|sleep|wait|sync|vsync|"
    r"texture|upload|buffer|shader|draw|batch|memory|alloc|free|"
    r"update|tick|scene|particle|effect|animation|stream|compress|"
    r"load|unload|gc|garbage|deviceconfig|xgs",
    re.I,
)
PRIORITY = re.compile(
    r"DoPresent|Render|Present|Swap|Draw|Update|Tick|"
    r"LimitFPS|GetDesiredFramerate|FrameRate|Texture|"
    r"Alloc|Free|Memory|Stream|DeviceConfig|XGS",
    re.I,
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    lines = []
    with args.elf.open("rb") as f:
        elf = ELFFile(f)
        lines += [
            "READ-ONLY STATIC INVENTORY — not a runtime performance measurement",
            f"ELF class={elf.elfclass} machine={elf.header['e_machine']} endian={elf.little_endian}",
        ]
        symbols = {}
        for sec in elf.iter_sections():
            if sec.header.sh_type not in ("SHT_SYMTAB", "SHT_DYNSYM"):
                continue
            for sym in sec.iter_symbols():
                name = sym.name
                size = int(sym.entry.st_size)
                addr = int(sym.entry.st_value)
                if name and size and PATTERNS.search(name):
                    symbols[(addr, name)] = (size, name)
        lines.append(f"Matched named functions: {len(symbols)}")
        for (addr, name), (size, _) in sorted(symbols.items()):
            if PRIORITY.search(name):
                lines.append(f"FUNCTION 0x{addr:x} size=0x{size:x} {name}")
        textsec = elf.get_section_by_name(".text")
        if textsec:
            md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
            text = textsec.data()
            base = int(textsec.header.sh_addr)
            selected = [(a, s, n) for (a, n), (s, _) in symbols.items()
                        if PRIORITY.search(n) and base <= a < base + len(text)]
            for addr, size, name in sorted(selected):
                off = addr - base
                chunk = text[off:off + min(size, 0x500)]
                lines.append(f"\nDISASSEMBLY {name} @0x{addr:x} size=0x{size:x}")
                for ins in md.disasm(chunk, addr):
                    lines.append(f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}")
        else:
            lines.append("WARNING: .text section not found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {args.output}")

if __name__ == "__main__":
    main()
