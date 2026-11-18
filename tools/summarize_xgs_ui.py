#!/usr/bin/env python3
"""Produce a text-only map of Exient UI registrations and frontend navigation hints.

This is deliberately diagnostic: it does not rewrite, unpack, or repack game assets.
"""
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
rows = [
    "EXIENT XGS UI DIAGNOSTICS",
    "Read-only string-context report; not a decoded/editable UI document.",
    "",
]
screen_rows = []
nav_rows = []
for path in sorted(root.rglob("*.xml")):
    try:
        data = path.read_bytes()
    except OSError:
        continue
    text = data.decode("utf-8", "replace").replace("\x00", "\n")
    hits = [term for term in terms if term in text]
    if not hits:
        continue
    rel = str(path.relative_to(root))
    lines = [line.strip() for line in text.splitlines()]
    rows.append(f"FILE {rel}")
    rows.append("MATCHES " + ", ".join(hits))
    for i, line in enumerate(lines):
        if "registerScreen" in line:
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            screen_rows.append(f"{rel}: L{i+1}: {context[:1000]}")
        if any(term.lower() in line.lower() for term in nav_terms):
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            nav_rows.append(f"{rel}: L{i+1}: {context[:1000]}")
        if any(term in line for term in terms):
            context = " | ".join(x for x in lines[max(0, i-2):min(len(lines), i+4)] if x)
            rows.append(f"  L{i+1}: {context[:1200]}")
    rows.append("")

rows.extend(["", "=== SCREEN REGISTRATIONS ==="])
rows.extend(screen_rows or ["No registerScreen strings found."])
rows.extend(["", "=== FRONTEND / NAVIGATION HINTS ==="])
rows.extend(nav_rows or ["No navigation hints found."])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"UI map: {len(rows)} report lines -> {out}")
