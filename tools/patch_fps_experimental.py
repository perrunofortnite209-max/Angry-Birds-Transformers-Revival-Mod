#!/usr/bin/env python3
"""Guarded FPS patch for the exact analyzed Angry Birds Transformers 2.42.0 APK."""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path

EXPECTED_APK_SHA256 = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
TARGETS = {
    "lib/arm64-v8a/libABBS.so": {
        "abi": "AArch64", "signature": bytes.fromhex(
            "4830009008ed42f9080140f9080100b4083d40f9c80000b4"
            "08bd42b91f0900716100005480078052c0035fd6e0031f2ac0035fd6"
        ), "instruction_offset": 0x24,
        "old": bytes.fromhex("80078052"), "new": bytes.fromhex("00128052"),
    },
    "lib/armeabi-v7a/libABBS.so": {
        "abi": "ARM32", "signature": bytes.fromhex(
            "38009fe500009fe7001090e50000a0e3000051e31eff2f01"
            "500091e5000050e30400000a041290e53c00a0e3020051e3"
            "0000a0131eff2fe10000a0e31eff2fe1"
        ), "instruction_offset": 0x28,
        "old": bytes.fromhex("3c00a0e3"), "new": bytes.fromhex("9000a0e3"),
    },
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def find_unique(data: bytes, needle: bytes, label: str) -> int:
    hits, start = [], 0
    while True:
        pos = data.find(needle, start)
        if pos < 0:
            break
        hits.append(pos)
        start = pos + 1
    if len(hits) != 1:
        raise RuntimeError(f"{label}: se esperaba 1 firma completa y se encontraron {len(hits)}")
    return hits[0]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_apk", type=Path)
    ap.add_argument("output_apk", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    source = args.input_apk.read_bytes()
    digest = sha256(source)
    if digest != EXPECTED_APK_SHA256:
        raise SystemExit(f"APK distinto del analizado: SHA-256 {digest}")
    report = {"original_apk_sha256": digest, "target_fps_constant": 144,
              "patches": [], "removed_old_signatures": []}
    with zipfile.ZipFile(io.BytesIO(source), "r") as zin:
        names = zin.namelist()
        replacements = {}
        for path, spec in TARGETS.items():
            if names.count(path) != 1:
                raise RuntimeError(f"{path}: entrada ausente o duplicada")
            original = zin.read(path)
            function_offset = find_unique(original, spec["signature"], path)
            offset = function_offset + spec["instruction_offset"]
            before = original[offset:offset+4]
            if before != spec["old"]:
                raise RuntimeError(
                    f"{path} offset {offset:#x}: bytes {before.hex()} inesperados; "
                    f"se esperaban {spec['old'].hex()}"
                )
            patched = bytearray(original)
            patched[offset:offset+4] = spec["new"]
            if bytes(patched[offset:offset+4]) != spec["new"]:
                raise RuntimeError(f"{path}: verificación posterior fallida")
            # The exact function signature must now be absent; the modified bytes must be present.
            if bytes(patched).find(spec["signature"]) != -1:
                raise RuntimeError(f"{path}: la firma original sigue presente")
            replacements[path] = bytes(patched)
            report["patches"].append({
                "path": path, "abi": spec["abi"],
                "function_file_offset": hex(function_offset),
                "instruction_file_offset": hex(offset),
                "before": before.hex(), "after": spec["new"].hex(),
                "library_sha256_before": sha256(original),
                "library_sha256_after": sha256(bytes(patched)),
                "verified": True,
            })
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as zout:
            for info in zin.infolist():
                upper = info.filename.upper()
                is_signature = upper.startswith("META-INF/") and (
                    upper.endswith((".RSA", ".DSA", ".EC", ".SF"))
                    or upper == "META-INF/MANIFEST.MF"
                )
                if is_signature:
                    report["removed_old_signatures"].append(info.filename)
                    continue
                zout.writestr(info, replacements.get(info.filename, zin.read(info.filename)))
    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(output.getvalue())
    # Re-open and validate the generated APK container and patched native entries.
    with zipfile.ZipFile(args.output_apk, "r") as check:
        bad = check.testzip()
        if bad:
            raise RuntimeError(f"ZIP/APK corrupto en entrada {bad}")
        for patch in report["patches"]:
            data = check.read(patch["path"])
            off = int(patch["instruction_file_offset"], 16)
            expected = bytes.fromhex(patch["after"])
            if data[off:off+4] != expected:
                raise RuntimeError(f"Verificación del APK generado falló: {patch['path']} offset {off:#x}")
    report["patched_unsigned_apk_sha256"] = sha256(args.output_apk.read_bytes())
    report["patched_apk_size"] = args.output_apk.stat().st_size
    report["apk_zip_test"] = "passed"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
