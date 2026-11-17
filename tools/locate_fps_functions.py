#!/usr/bin/env python3
"""Locate complete analyzed FPS functions in the original APK without modifying it."""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path

EXPECTED_APK_SHA256 = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
TARGETS = {
    "lib/arm64-v8a/libABBS.so": {
        "abi": "AArch64",
        "function": "CApp::GetDesiredFramerate",
        "ghidra_address": "0x007e6620",
        "image_base": "0x00100000",
        "signature": bytes.fromhex(
            "4830009008ed42f9080140f9080100b4083d40f9c80000b4"
            "08bd42b91f0900716100005480078052c0035fd6e0031f2ac0035fd6"
        ),
        "patch_offset_in_function": 0x24,
        "expected_instruction": bytes.fromhex("80078052"),
    },
    "lib/armeabi-v7a/libABBS.so": {
        "abi": "ARM32",
        "function": "CApp::GetDesiredFramerate",
        "ghidra_address": "0x0051de94",
        "image_base": "0x00010000",
        "signature": bytes.fromhex(
            "38009fe500009fe7001090e50000a0e3000051e31eff2f01"
            "500091e5000050e30400000a041290e53c00a0e3020051e3"
            "0000a0131eff2fe10000a0e31eff2fe1"
        ),
        "patch_offset_in_function": 0x28,
        "expected_instruction": bytes.fromhex("3c00a0e3"),
    },
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def occurrences(haystack: bytes, needle: bytes) -> list[int]:
    found, start = [], 0
    while True:
        pos = haystack.find(needle, start)
        if pos < 0:
            return found
        found.append(pos)
        start = pos + 1

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("apk", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    apk = args.apk.read_bytes()
    digest = sha256(apk)
    if digest != EXPECTED_APK_SHA256:
        raise SystemExit(f"APK SHA-256 distinto al analizado: {digest}")
    report = {"apk_sha256": digest, "mode": "read-only exact function signature scan", "targets": []}
    with zipfile.ZipFile(io.BytesIO(apk)) as z:
        for path, spec in TARGETS.items():
            if z.namelist().count(path) != 1:
                raise SystemExit(f"Entrada ausente o duplicada: {path}")
            blob = z.read(path)
            hits = occurrences(blob, spec["signature"])
            item = {
                "path": path, "abi": spec["abi"], "function": spec["function"],
                "ghidra_address": spec["ghidra_address"], "image_base": spec["image_base"],
                "library_size": len(blob), "library_sha256": sha256(blob),
                "signature_size": len(spec["signature"]), "matches": [hex(x) for x in hits],
                "match_count": len(hits),
            }
            if len(hits) == 1:
                off = hits[0] + spec["patch_offset_in_function"]
                actual = blob[off:off+4]
                item.update({
                    "function_file_offset": hex(hits[0]),
                    "candidate_instruction_file_offset": hex(off),
                    "expected_instruction": spec["expected_instruction"].hex(),
                    "actual_instruction": actual.hex(),
                    "instruction_matches": actual == spec["expected_instruction"],
                    "context_before": blob[max(0, off-16):off].hex(),
                    "context_after": blob[off+4:off+20].hex(),
                })
                if actual != spec["expected_instruction"]:
                    raise SystemExit(f"Bytes inesperados en {path} offset {off:#x}: {actual.hex()}")
            else:
                raise SystemExit(f"Firma completa no única para {path}: {len(hits)} coincidencias")
            report["targets"].append(item)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
