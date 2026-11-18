#!/usr/bin/env python3
"""Produce a text-only map of Exient XGS UI registrations and XOX2 string pools.

Read-only diagnostics only: never rewrites or repacks game assets.
"""
import struct
import sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])
terms = (
    "registerScreen", "CWindow_MainSplashScreen", "CWindow_PlayButton",
    "CSettingsScreen", "ShowSettingsScreen", "EScreen_FE_Settings",
    "EScreen_FE_Splash", "EScreen_FE_Map", "SplashScreenPlay",
    "onClickedGlobalState", "onTappedGlobalState",
)
nav_terms = (
    "EScreen_FE_Splash", "EScreen_FE_Map", "EScreen_FE_Settings",
    "SplashScreenPlay", "ShowSettingsScreen", "ShowMapScreen",
    "ShowMainMenu", "MainMenu", "MapScreen",
)

def printable_nul_strings(data):
    values = []
    for raw in data.split(b"\x00"):
        if not raw:
            continue
        value = raw.decode("utf-8", "replace").strip()
        if value and not any(ord(ch) < 32 and ch not in "\t" for ch in value):
            values.append(value)
    return values

def xox2_info(data):
    if len(data) < 12 or data[:4] != b"XOX2":
        return None
    count = struct.unpack_from("<I", data, 4)[0]
    if count == 0 or count > 100000:
        return None
    table_start = 12
    table_end = table_start + count * 4
    if table_end > len(data):
        return None
    offsets = struct.unpack_from("<" + "I" * count, data, table_start)
    # Keep the pool as a raw NUL-delimited string inventory. Offset interpretation
    # is deliberately not assumed until the engine's exact XOX2 semantics are proven.
    strings = printable_nul_strings(data[table_end:])
    return count, table_end, offsets, strings

rows = [
    "EXIENT XGS UI DIAGNOSTICS",
    "Read-only report. XOX2 offset semantics are not assumed; string pools are inventoried as NUL-delimited text.",
    "No game resources are modified or repacked.",
    "",
]
screen_rows = []
nav_rows = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    try:
        data = path.read_bytes()
    except OSError:
        continue
    rel = str(path.relative_to(root))
    info = xox2_info(data)
    if info is not None:
        count, table_end, offsets, pool_strings = info
        rows.append(f"XOX2 RESOURCE {rel}: string_count={count} table_end={table_end} bytes={len(data)} pool_strings={len(pool_strings)}")
        rows.append("  offset_table_first=" + ", ".join(str(x) for x in offsets[:16]))
        rows.append("  offset_table_last=" + ", ".join(str(x) for x in offsets[-8:]))
        if "settings" in path.name.lower():
            rows.append("  === COMPLETE SETTINGS STRING POOL (NUL-DELIMITED) ===")
            rows.extend(f"  P{i:04d}: {value[:1000]}" for i, value in enumerate(pool_strings))
            rows.append("  === OFFSET TABLE DECODE CANDIDATES (POOL-RELATIVE) ===")
            pool = data[table_end:]
            for i, offset in enumerate(offsets):
                if offset >= len(pool):
                    rows.append(f"  O{i:04d} offset={offset}: OUT_OF_RANGE")
                    continue
                end = pool.find(b"\x00", offset)
                if end < 0:
                    rows.append(f"  O{i:04d} offset={offset}: NO_TERMINATOR")
                    continue
                raw = pool[offset:end]
                value = raw.decode("utf-8", "replace")
                rows.append(f"  O{i:04d} offset={offset}: {value[:300]!r}")
            rows.append("  === END OFFSET TABLE DECODE ===")
            rows.append("  === END SETTINGS STRING POOL ===")
        lines = pool_strings
    else:
        lines = printable_nul_strings(data)
        if not lines:
            text = data.decode("utf-8", "replace")
            lines = text.splitlines()
    joined = "\n".join(lines)
    hits = [term for term in terms if term in joined]
    if not hits:
        continue
    rows.append(f"FILE {rel}")
    rows.append("MATCHES " + ", ".join(hits))
    for i, line in enumerate(lines):
        if "registerScreen" in line:
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            screen_rows.append(f"{rel}: S{i+1}: {context[:2000]}")
        if any(term.lower() in line.lower() for term in nav_terms):
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            nav_rows.append(f"{rel}: S{i+1}: {context[:2000]}")
        if any(term in line for term in terms):
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            rows.append(f"  S{i+1}: {context[:2000]}")
    rows.append("")

rows.extend(["", "=== SCREEN REGISTRATIONS ==="])
rows.extend(screen_rows or ["No registerScreen strings found."])
rows.extend(["", "=== FRONTEND / NAVIGATION HINTS ==="])
rows.extend(nav_rows or ["No navigation hints found."])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"UI map: {len(rows)} report lines -> {out}")
