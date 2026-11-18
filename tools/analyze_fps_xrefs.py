#!/usr/bin/env python3
"""Find AArch64 code references to FPS-related native strings in libABBS.so."""
from __future__ import annotations
import re, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, arm64_const

NEEDLES = (b"TARGET_60_FPS", b"LowBatteryFPSCap", b"fps", b"FPS", b"Framerate", b"FrameRate", b"RefreshRate")

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: analyze_fps_xrefs.py libABBS.so report.txt")
    elf_path, report_path = map(Path, sys.argv[1:])
    out = []
    with elf_path.open("rb") as f:
        elf = ELFFile(f)
        if elf.header["e_machine"] != "EM_AARCH64":
            raise SystemExit("Expected AArch64 ELF")
        ro_sections = [s for s in elf.iter_sections() if s.name in (".rodata", ".data.rel.ro", ".data")]
        found = []
        for sec in ro_sections:
            blob = sec.data()
            base = int(sec.header.sh_addr)
            for needle in NEEDLES:
                for m in re.finditer(re.escape(needle), blob, re.IGNORECASE):
                    va = base + m.start()
                    raw = blob[m.start():m.start()+100].split(b"\\0",1)[0]
                    found.append((va, raw.decode("ascii","replace"), sec.name))
        # Deduplicate identical address/string matches.
        found = sorted(set(found))
        out.append(f"ELF={elf_path.name} class={elf.elfclass} machine={elf.header['e_machine']}")
        out.append(f"FPS-related strings found: {len(found)}")
        for va, s, secname in found:
            out.append(f"STRING {secname} VA=0x{va:x}: {s}")
        textsec = elf.get_section_by_name(".text")
        if not textsec:
            raise SystemExit("Missing .text")
        text = textsec.data()
        text_base = int(textsec.header.sh_addr)
        md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        md.detail = True
        insns = list(md.disasm(text, text_base))
        # Locate named native functions to label nearby references.
        funcs = []
        for sec in elf.iter_sections():
            if sec.header.sh_type in ("SHT_SYMTAB", "SHT_DYNSYM"):
                for sym in sec.iter_symbols():
                    if sym.entry.st_info.type == "STT_FUNC" and sym.name:
                        funcs.append((int(sym.entry.st_value), int(sym.entry.st_size), sym.name))
        funcs.sort()
        for va, s, secname in found:
            page = va & ~0xfff
            matches = []
            for i, ins in enumerate(insns):
                if ins.mnemonic != "adrp" or len(ins.operands) < 2:
                    continue
                op = ins.operands[1]
                if op.type == arm64_const.ARM64_OP_IMM and (op.imm & ~0xfff) == page:
                    matches.append(i)
            out.append(f"\\nXREF_CANDIDATES string=0x{va:x} page=0x{page:x}: {len(matches)}")
            for idx in matches:
                ins = insns[idx]
                owner = "unknown"
                for fa, fs, fn in funcs:
                    if fa <= ins.address and (fs == 0 or ins.address < fa + fs):
                        owner = fn
                out.append(f"  candidate at 0x{ins.address:x} function={owner}")
                for near in insns[max(0,idx-5):min(len(insns),idx+9)]:
                    out.append(f"    {near.address:08x}: {near.mnemonic:8} {near.op_str}")
    report_path.write_text("\\n".join(out)+"\\n", encoding="utf-8")
    print(f"Wrote {len(out)} lines to {report_path}")

if __name__ == "__main__":
    main()
