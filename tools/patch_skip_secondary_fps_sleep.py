#!/usr/bin/env python3
"""One-instruction A/B patch: skip only DoPresent's secondary FPS sleep call."""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path

EXPECTED_APK_SHA256 = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"

# Each signature includes the conditional guard and the exact BL instruction.
# Only the final BL is replaced with the architecture's NOP instruction.
TARGETS = {
    "lib/arm64-v8a/libABBS.so": {
        "abi": "arm64-v8a",
        "signature": bytes.fromhex("9f0600716b000054e003142ad073f697"),
        "patch_offset": 12,
        "old": bytes.fromhex("d073f697"),
        "new": bytes.fromhex("1f2003d5"),
        "function_va": "0x007e6028",
        "replacement": "AArch64 NOP",
    },
    "lib/armeabi-v7a/libABBS.so": {
        "abi": "armeabi-v7a",
        "signature": bytes.fromhex("010055e3010000ba0500a0e171d6f5eb"),
        "patch_offset": 12,
        "old": bytes.fromhex("71d6f5eb"),
        "new": bytes.fromhex("00f020e3"),
        "function_va": "0x0051d8c8",
        "replacement": "ARM NOP",
    },
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def unique_offset(data: bytes, signature: bytes, label: str) -> int:
    hits, pos = [], 0
    while True:
        pos = data.find(signature, pos)
        if pos < 0:
            break
        hits.append(pos)
        pos += 1
    if len(hits) != 1:
        raise RuntimeError(f"{label}: firma esperada una vez; encontrada {len(hits)}")
    return hits[0]

def is_signature_file(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("META-INF/") and (
        upper.endswith((".RSA", ".DSA", ".EC", ".SF")) or upper == "META-INF/MANIFEST.MF"
    )

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_apk", type=Path)
    ap.add_argument("output_apk", type=Path)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()

    source = args.input_apk.read_bytes()
    source_hash = sha256(source)
    if source_hash != EXPECTED_APK_SHA256:
        raise SystemExit(f"APK no coincide con el original auditado: {source_hash}")

    report = {
        "experiment": "skip-secondary-fps-sleep",
        "original_apk_sha256": source_hash,
        "change": "Replace only DoPresent -> LimitFPSWithSleep BL with NOP",
        "warning": "Experimental A/B build; frame pacing and smoothness are not guaranteed to improve.",
        "patched_libraries": [],
        "pak_integrity": [],
        "removed_signature_entries": [],
    }

    with zipfile.ZipFile(io.BytesIO(source), "r") as zin:
        names = zin.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("APK contiene entradas ZIP duplicadas; se cancela.")
        replacements = {}
        for path, spec in TARGETS.items():
            if names.count(path) != 1:
                raise RuntimeError(f"Falta biblioteca requerida: {path}")
            original = zin.read(path)
            base = unique_offset(original, spec["signature"], path)
            off = base + spec["patch_offset"]
            before = original[off:off+4]
            if before != spec["old"]:
                raise RuntimeError(f"{path}: opcode inesperado en {off:#x}: {before.hex()}")
            patched = bytearray(original)
            patched[off:off+4] = spec["new"]
            if bytes(patched[off:off+4]) != spec["new"]:
                raise RuntimeError(f"{path}: no se pudo verificar el NOP")
            if bytes(patched).find(spec["signature"]) != -1:
                raise RuntimeError(f"{path}: la llamada original sigue presente")
            replacements[path] = bytes(patched)
            report["patched_libraries"].append({
                "path": path, "abi": spec["abi"], "callsite_va": spec["function_va"],
                "file_offset": hex(off), "before": before.hex(), "after": spec["new"].hex(),
                "replacement": spec["replacement"], "sha256_before": sha256(original),
                "sha256_after": sha256(bytes(patched)), "verified": True,
            })

        # Keep every non-target entry's uncompressed bytes unchanged.
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as zout:
            for info in zin.infolist():
                if is_signature_file(info.filename):
                    report["removed_signature_entries"].append(info.filename)
                    continue
                data = replacements.get(info.filename)
                if data is None:
                    data = zin.read(info.filename)
                    if info.filename.lower().endswith(".pak"):
                        report["pak_integrity"].append({
                            "path": info.filename, "sha256": sha256(data), "unchanged": True
                        })
                zout.writestr(info, data)

    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(output.getvalue())

    with zipfile.ZipFile(args.output_apk, "r") as check:
        bad = check.testzip()
        if bad:
            raise RuntimeError(f"APK ZIP inválido: {bad}")
        for path, spec in TARGETS.items():
            data = check.read(path)
            if spec["new"] not in data:
                raise RuntimeError(f"No se encontró el NOP final en {path}")
        for item in report["pak_integrity"]:
            if sha256(check.read(item["path"])) != item["sha256"]:
                raise RuntimeError(f"PAK alterado: {item['path']}")

    report["patched_unsigned_apk_sha256"] = sha256(args.output_apk.read_bytes())
    report["patched_unsigned_apk_size"] = args.output_apk.stat().st_size
    report["zip_integrity"] = "passed"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
