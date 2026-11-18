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
        call_targets={0x6ed26c:"CDeviceConfig::LoadDeviceConfigByPerformance",0x6ed4b8:"CDeviceConfig::ChangePerformance",0x6ed640:"CDeviceConfig::UpdateRecommendedPerformance",0x6ed610:"CDeviceConfig::GetCurrentPerformance"}
        for ins in insns:
            if ins.mnemonic=="bl" and ins.operands and ins.operands[0].type==arm64_const.ARM64_OP_IMM:
                dest=int(ins.operands[0].imm)
                if dest in call_targets:
                    owner="unknown"
                    for fa,fs,fn in funcs:
                        if fa<=ins.address and (fs==0 or ins.address<fa+fs): owner=fn
                    out.append(f"CALLSITE 0x{ins.address:x} -> {call_targets[dest]} owner={owner}")
        out.append("\\n## Native config-related symbols")
        for fa,fs,fn in funcs:
            if any(key in fn.lower() for key in ("deviceconfig","loadxmlconfig","configprofile","configmanager")):
                out.append(f"SYMBOL 0x{fa:x} size=0x{fs:x} {fn}")
                if ("loadxmlconfig" in fn.lower() and "cmapmanager" in fn.lower()) or "cdeviceconfig" in fn.lower() or "mainloadingdeviceconfig" in fn.lower() or "ingameresultsscreen" in fn.lower():
                    if fs:
                        off=fa-textbase
                        for ins in md.disasm(text[off:off+fs],fa):
                            out.append(f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}")
        # Resolve exact ADRP+ADD addresses, not every string sharing the same 4 KB page.
        exact_refs = {}
        for idx, ins in enumerate(insns):
            if ins.mnemonic != "adrp" or len(ins.operands) < 2:
                continue
            dst = ins.operands[0]
            pageop = ins.operands[1]
            if dst.type != arm64_const.ARM64_OP_REG or pageop.type != arm64_const.ARM64_OP_IMM:
                continue
            reg = dst.reg
            page = int(pageop.imm) & ~0xfff
            for nxt in insns[idx + 1:min(len(insns), idx + 5)]:
                if nxt.mnemonic not in ("add", "adds") or len(nxt.operands) < 3:
                    continue
                if (nxt.operands[0].type == arm64_const.ARM64_OP_REG and
                    nxt.operands[1].type == arm64_const.ARM64_OP_REG and
                    nxt.operands[0].reg == reg and nxt.operands[1].reg == reg and
                    nxt.operands[2].type == arm64_const.ARM64_OP_IMM):
                    target = page + int(nxt.operands[2].imm)
                    for va, value, secname in found:
                        if va == target:
                            owner = "unknown"
                            for fa, fs, fn in funcs:
                                if fa <= ins.address and (fs == 0 or ins.address < fa + fs):
                                    owner = fn
                            exact_refs.setdefault(va, []).append((ins.address, nxt.address, owner))
                    break
        out.append("\\n## Exact graphics/config string references (ADRP + ADD)")
        for va, value, secname in found:
            refs = exact_refs.get(va, [])
            if refs:
                out.append(f"EXACT_STRING 0x{va:x} {value}")
                for adrp_at, add_at, owner in refs:
                    out.append(f"  ADRP 0x{adrp_at:x} + ADD 0x{add_at:x} function={owner}")
                    for near in insns[max(0, next((i for i, x in enumerate(insns) if x.address == adrp_at), 0)-3):min(len(insns), next((i for i, x in enumerate(insns) if x.address == add_at), 0)+9)]:
                        out.append(f"    {near.address:08x}: {near.mnemonic:8} {near.op_str}")
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
        # Dump exact instruction windows for the three methods and known native callers.
        out.append("\\n## Focused ARM64 disassembly (exact RVAs)")
        for center, label, before, after in (
            (0x6ed26c, "LoadDeviceConfigByPerformance", 0, 0x110),
            (0x6ed4b8, "ChangePerformance", 0, 0x180),
            (0x6ed610, "GetCurrentPerformance", 0, 0x90),
            (0x5bdad8, "InGameResultsScreen caller", 0x100, 0x100),
            (0x6e3ef4, "MainLoadingDeviceConfig caller", 0x100, 0x100),
        ):
            start=max(textbase, center-before)
            end=min(textbase+len(text), center+after)
            out.append(f"\\nFUNCTION_WINDOW {label} center=0x{center:x} range=0x{start:x}-0x{end:x}")
            off=start-textbase
            for ins in md.disasm(text[off:end-start], start):
                out.append(f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}")
        report_path.write_text("\n".join(out)+"\n",encoding="utf-8")
    print(f"Wrote {len(out)} lines to {report_path}")

if __name__=="__main__": main()
