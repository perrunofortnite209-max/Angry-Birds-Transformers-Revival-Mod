#!/usr/bin/env python3
"""Compact, read-only XGS ARM64 symbol and hot-path candidate inventory."""
from __future__ import annotations
import argparse, re
from collections import Counter
from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

CATEGORIES = {
    "frame_pacing": re.compile(r"present|swap|frame|fps|sleep|wait|sync|vsync|framerate", re.I),
    "rendering": re.compile(r"render|draw|batch|shader", re.I),
    "texture_upload": re.compile(r"texture|upload|buffer", re.I),
    "memory": re.compile(r"memory|alloc|free|heap|pool", re.I),
    "update_scene": re.compile(r"update|tick|scene|particle|effect|animation", re.I),
    "streaming": re.compile(r"stream|compress|load|unload|gc|garbage", re.I),
    "engine": re.compile(r"deviceconfig|xgs", re.I),
}
FOCUS = [
    re.compile(p, re.I) for p in (
        r"_ZN4CApp12ProcessFrameEv",
        r"_ZN4CApp8DoRenderEv",
        r"_ZN5CGame11RenderFrameEv",
        r"_ZN14CRenderManager11RenderFrameEv",
        r"_ZN4CApp9DoPresentEv",
        r"_ZN4CApp19GetDesiredFramerateEv",
        r"_ZN13CDeviceConfig19GetDesiredFramerateEv",
        r"LimitFPSWithSleep",
        r"ExientGLSurfaceView|nativeDrawFrame",
    )
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    lines = [
        "XGS STATIC SYMBOL TRIAGE — no runtime timings or FPS measurements",
        "Interpret symbol names as leads only; confirm callers and runtime behavior before patching.",
    ]
    console = [
        "=== XGS PERFORMANCE TRIAGE (STATIC; NOT RUNTIME PROFILING) ===",
        "Names are search leads, not proof of hot paths or bottlenecks.",
    ]
    with args.elf.open("rb") as f:
        elf = ELFFile(f)
        lines.append(f"ELF class={elf.elfclass} machine={elf.header['e_machine']} endian={elf.little_endian}")
        symbols = {}
        all_named = {}
        for sec in elf.iter_sections():
            if sec.header.sh_type not in ("SHT_SYMTAB", "SHT_DYNSYM"):
                continue
            for sym in sec.iter_symbols():
                name = sym.name
                size = int(sym.entry.st_size)
                addr = int(sym.entry.st_value)
                if name and size:
                    all_named.setdefault(addr, (name, size))
                    cats = [key for key, rx in CATEGORIES.items() if rx.search(name)]
                    if cats:
                        symbols[(addr, name)] = (size, cats)
        counts = Counter(cat for _, cats in symbols.values() for cat in cats)
        lines.append(f"Total unique named functions matching categories: {len(symbols)}")
        lines.append("Category counts (a function may count in multiple categories):")
        console.append(f"Matching named functions: {len(symbols)}")
        console.append("Category counts:")
        for cat, count in counts.most_common():
            lines.append(f"  {cat}: {count}")
            console.append(f"  {cat}: {count}")
        ranked = sorted(
            [(addr, name, size, cats) for (addr, name), (size, cats) in symbols.items()],
            key=lambda x: (0 if "frame_pacing" in x[3] else 1 if "rendering" in x[3] else 2,
                           -x[2], x[1])
        )
        lines.append("\nNAMED FUNCTION CANDIDATES (first 220; address, size, category):")
        for addr, name, size, cats in ranked[:220]:
            lines.append(f"0x{addr:x} size=0x{size:x} [{','.join(cats)}] {name}")
        console.append("\nTop 60 named candidates (address, size, category):")
        for addr, name, size, cats in ranked[:60]:
            console.append(f"0x{addr:x} size=0x{size:x} [{','.join(cats)}] {name}")
        textsec = elf.get_section_by_name(".text")
        if textsec:
            md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
            md.detail = True
            text = textsec.data()
            base = int(textsec.header.sh_addr)
            # Resolve direct BL references across .text; names alone are not evidence.
            target_names = {
                0x6e5f80: "CApp::DoPresent",
                0x482f68: "LimitFPSWithSleep",
                0x6e6620: "CApp::GetDesiredFramerate",
                0x6ed3e0: "CDeviceConfig::GetDesiredFramerate",
                0x817bd8: "ExientGLSurfaceView::nativeDrawFrame",
                0x4351f4: "CGame::RenderFrame",
                0x484d80: "CRenderManager::RenderFrame",
            }
            callers = {addr: [] for addr in target_names}
            for ins in md.disasm(text, base):
                if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == 2:
                    dest = int(ins.operands[0].imm)
                    if dest in callers:
                        owner_addr = max((a for a in all_named if a <= ins.address), default=None)
                        owner = all_named.get(owner_addr, ("unknown", 0))[0]
                        callers[dest].append((ins.address, owner))
            lines.append("\\nDIRECT CALLER XREFS (BL instructions; static only):")
            console.append("\\nDirect caller cross-references (BL; static only):")
            for dest, label in target_names.items():
                entries = callers[dest]
                row = f"{label} @0x{dest:x}: {len(entries)} direct callers"
                lines.append(row)
                console.append(row)
                for callsite, owner in entries[:20]:
                    item = f"  callsite=0x{callsite:x} in {owner}"
                    lines.append(item)
                    console.append(item)
            all_symbols = [(addr, name, size, cats) for (addr, name), (size, cats) in symbols.items()]
            selected = []
            used = set()
            for pattern in FOCUS:
                match = next((item for item in all_symbols
                              if pattern.search(item[1]) and base <= item[0] < base + len(text)), None)
                if match and (match[0], match[1]) not in used:
                    selected.append(match)
                    used.add((match[0], match[1]))
            for item in ranked:
                if len(selected) >= 8:
                    break
                if ("frame_pacing" in item[3] or "rendering" in item[3]) and base <= item[0] < base + len(text) and (item[0], item[1]) not in used:
                    selected.append(item)
                    used.add((item[0], item[1]))
            lines.append("\nFOCUSED DISASSEMBLY (render functions up to 0x800 bytes; others 0x300):")
            console.append("\nFocused disassembly (render functions up to 0x800 bytes; others 0x300):")
            for addr, name, size, cats in selected:
                header = f"\n{name} @0x{addr:x} size=0x{size:x} [{','.join(cats)}]"
                lines.append(header)
                console.append(header)
                off = addr - base
                limit = 0x800 if ("DoRender" in name or "RenderFrame" in name) else 0x300
                instructions = list(md.disasm(text[off:off + min(size, limit)], addr))
                for ins in instructions:
                    row = f"  {ins.address:08x}: {ins.mnemonic:8} {ins.op_str}"
                    if ins.mnemonic == "bl" and ins.operands and ins.operands[0].type == 2:
                        dest = int(ins.operands[0].imm)
                        target = all_named.get(dest, (target_names.get(dest, ""), 0))[0]
                        if target:
                            row += f"  ; {target}"
                    lines.append(row)
                    console.append(row)
        else:
            lines.append("WARNING: .text section not found")
            console.append("WARNING: .text section not found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} lines; {len(symbols)} unique matching symbols")
    print("\n".join(console))

if __name__ == "__main__":
    main()
