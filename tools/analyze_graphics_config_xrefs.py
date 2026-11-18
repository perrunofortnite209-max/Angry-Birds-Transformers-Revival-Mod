#!/usr/bin/env python3
"""Locate native XGS device-config/graphics setting readers (read-only)."""
from __future__ import annotations
import re, sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, arm64_const

NEEDLES = (
    b"RENDER_SHADOWMAP", b"RENDER_FESHADOWMAP", b"SHADOW_MAP_SIZE",
    b"RENDER_GAMEREFLECTIONS", b"RENDER_FEREFLECTIONS", b"RENDER_LENSFLARES",
    b"RENDER_SCALE_X", b"RENDER_SCALE_Y", b"VFX_LIMIT_CONFIG",
    b"POST_PROCESS_BLOOM", b"POST_PROCESS_MOTION_BLUR", b"SOFT_PARTICLES",
    b"SHADER_LOD", b"MODEL_LOD", b"DEVICE_CONFIG_SCALING",
    b"DeviceConfig", b"android-generic_high", b"android-generic_low",
)

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: analyze_graphics_config_xrefs.py libABBS.so report.txt")
    elf_path, report_path = map(Path, sys.argv[1:])
    out=[]
    with elf_path.open("rb") as f:
        elf=ELFFile(f)
        if elf.header["e_machine"] != "EM_AARCH64":
            raise SystemExit("Expected AArch64 ELF")
        sections=[]
        found=[]
        for sec in elf.iter_sections():
            if not (int(sec.header.sh_flags) & 0x2):
                continue
            blob=sec.data(); base=int(sec.header.sh_addr)
            for needle in NEEDLES:
                for m in re.finditer(re.escape(needle),blob,re.I):
                    raw=blob[m.start():m.start()+160].split(b"\0",1)[0]
                    found.append((base+m.start(),raw.decode("ascii","replace"),sec.name))
        found=sorted(set(found))
        out += [f"ELF={elf_path.name} machine={elf.header['e_machine']}",
                f"Graphics/config strings found: {len(found)}"]
        textsec=elf.get_section_by_name(".text")
        if textsec is None: raise SystemExit("Missing .text")
        text=textsec.data(); textbase=int(textsec.header.sh_addr)
        md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN); md.detail=True
        insns=list(md.disasm(text,textbase))
        funcs=[]
        for sec in elf.iter_sections():
            if sec.header.sh_type in ("SHT_SYMTAB","SHT_DYNSYM"):
                for sym in sec.iter_symbols():
                    if sym.entry.st_info.type=="STT_FUNC" and sym.name:
                        funcs.append((int(sym.entry.st_value),int(sym.entry.st_size),sym.name))
        funcs.sort()
        out.append("\\n## Native config-related symbols")
        for fa,fs,fn in funcs:
            if any(key in fn.lower() for key in ("deviceconfig","loadxmlconfig","configprofile","configmanager")):
                out.append(f"SYMBOL 0x{fa:x} size=0x{fs:x} {fn}")
                if ("loadxmlconfig" in fn.lower() and "cmapmanager" in fn.lower()) or "cdeviceconfig" in fn.lower() or "mainloadingdeviceconfig" in fn.lower():
                    if fs:
                    off=fa-textbase
                    for ins in md.disasm(text[off:off+fs],fa):
                        out.append(f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}")
        for va,s,secname in found:
            page=va & ~0xfff
            candidates=[]
            for i,ins in enumerate(insns):
                if ins.mnemonic!="adrp" or len(ins.operands)<2: continue
                op=ins.operands[1]
                if op.type==arm64_const.ARM64_OP_IMM and (op.imm & ~0xfff)==page:
                    candidates.append(i)
            out.append(f"\nSTRING {secname} VA=0x{va:x}: {s}")
            out.append(f"XREF_PAGE_CANDIDATES={len(candidates)}")
            for idx in candidates:
                ins=insns[idx]; owner="unknown"
                for fa,fs,fn in funcs:
                    if fa<=ins.address and (fs==0 or ins.address<fa+fs): owner=fn
                out.append(f"  at 0x{ins.address:x} function={owner}")
                for near in insns[max(0,idx-3):min(len(insns),idx+8)]:
                    out.append(f"    {near.address:08x}: {near.mnemonic:8} {near.op_str}")
        report_path.write_text("\n".join(out)+"\n",encoding="utf-8")
    print(f"Wrote {len(out)} lines to {report_path}")

if __name__=="__main__": main()
