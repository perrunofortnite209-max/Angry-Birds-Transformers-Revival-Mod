#!/usr/bin/env python3
"""Produce a text-only map of Exient UI screen registrations and menu actions."""
import os, re, sys
from pathlib import Path

root = Path(sys.argv[1])
out = Path(sys.argv[2])
terms = (
    "registerScreen", "CWindow_MainSplashScreen", "CWindow_PlayButton",
    "CSettingsScreen", "ShowSettingsScreen", "EScreen_FE_Settings",
    "onClickedGlobalState", "onTappedGlobalState",
)
rows = []
for path in sorted(root.rglob("*.xml")):
    try:
        data = path.read_bytes()
    except OSError:
        continue
    # XGS XML files have a binary XOX2 header and null-delimited UTF-8 strings.
    text = data.decode("utf-8", "replace").replace("\x00", "\n")
    hits = [term for term in terms if term in text]
    if not hits:
        continue
    rows.append(f"FILE {path.relative_to(root)}")
    rows.append("MATCHES " + ", ".join(hits))
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if any(term in line for term in terms):
            lo, hi = max(0, i-2), min(len(lines), i+4)
            rows.append(f"  L{i+1}: " + " | ".join(x.strip() for x in lines[lo:hi] if x.strip())[:1200])
    rows.append("")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(rows) if rows else "No matching UI XML registrations found.\n", encoding="utf-8")
print(f"UI map: {len(rows)} report lines -> {out}")
