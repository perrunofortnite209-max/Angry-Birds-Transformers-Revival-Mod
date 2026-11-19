#!/usr/bin/env python3
"""Combined guarded ABT experiment: 144-FPS target patch + skip secondary FPS sleep."""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path

EXPECTED_APK_SHA256 = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"

# Three independent, signature-guarded edits per ABI:
# 1) CApp::GetDesiredFramerate gameplay cap
# 2) CDeviceConfig::GetDesiredFramerate fallback cap
# 3) DoPresent's secondary LimitFPSWithSleep call
TARGETS = {
    "lib/arm64-v8a/libABBS.so": {
        "abi": "arm64-v8a",
        "patches": [
            {
                "name": "CApp::GetDesiredFramerate",
                "signature": bytes.fromhex(
                    "4830009008ed42f9080140f9080100b4083d40f9c80000b4"
                    "08bd42b91f0900716100005480078052c0035fd6e0031f2ac0035fd6"
                ),
                "offset": 0x24, "old": "80078052", "new": "00128052",
            },
            {
                "name": "CDeviceConfig::GetDesiredFramerate",
                "signature": bytes.fromhex(
                    "fd7bbfa9fd0300918ee4ff97a8320090"
                    "8907805208b548b91f010071c8038052"
                    "2801881a1f0000710001801afd7bc1a8c0035fd6"
                ),
                "offset": 0x1c, "old": "c8038052", "new": "08128052",
            },
            {
                "name": "DoPresent::SkipSecondaryLimitFPSWithSleep",
                "signature": bytes.fromhex("9f0600716b000054e003142ad073f697"),
                "offset": 12, "old": "d073f697", "new": "1f2003d5",
            },
        ],
    },
    "lib/armeabi-v7a/libABBS.so": {
        "abi": "armeabi-v7a",
        "patches": [
            {
                "name": "CApp::GetDesiredFramerate",
                "signature": bytes.fromhex(
                    "38009fe500009fe7001090e50000a0e3000051e31eff2f01"
                    "500091e5000050e30400000a041290e53c00a0e3020051e3"
                    "0000a0131eff2fe10000a0e31eff2fe1"
                ),
                "offset": 0x28, "old": "3c00a0e3", "new": "9000a0e3",
            },
            {
                "name": "CDeviceConfig::GetDesiredFramerate",
                "signature": bytes.fromhex(
                    "00482de976e3ffeb1c109fe51e20a0e3"
                    "01108fe0041091e5000051e33c200003"
                    "000050e30200a0010088bde8"
                ),
                "offset": 0x0c, "old": "1e20a0e3", "new": "9002a0e3",
            },
            {
                "name": "DoPresent::SkipSecondaryLimitFPSWithSleep",
                "signature": bytes.fromhex("010055e3010000ba0500a0e171d6f5eb"),
                "offset": 12, "old": "71d6f5eb", "new": "00f020e3",
            },
        ],
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
        raise RuntimeError(f"{label}: se esperaba una firma única; encontradas {len(hits)}")
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
    digest = sha256(source)
    if digest != EXPECTED_APK_SHA256:
        raise SystemExit(f"APK distinta de la original auditada: SHA-256 {digest}")

    report = {
        "experiment": "combined-144fps-and-skip-secondary-sleep",
        "original_apk_sha256": digest,
        "requested_fps_target": 144,
        "warning": "Experimental only; the device/display/game may not sustain 144 FPS.",
        "patches": [], "pak_integrity": [], "removed_signature_entries": [],
    }

    with zipfile.ZipFile(io.BytesIO(source), "r") as zin:
        names = zin.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("APK contiene entradas ZIP duplicadas; se cancela.")
        replacements = {}
        for path, spec in TARGETS.items():
            if names.count(path) != 1:
                raise RuntimeError(f"Biblioteca requerida ausente o duplicada: {path}")
            original = zin.read(path)
            patched = bytearray(original)
            for item in spec["patches"]:
                base = unique_offset(bytes(patched), item["signature"], path + ":" + item["name"])
                off = base + item["offset"]
                old, new = bytes.fromhex(item["old"]), bytes.fromhex(item["new"])
                before = bytes(patched[off:off+4])
                if before != old:
                    raise RuntimeError(f"{path} {item['name']}: opcode inesperado en {off:#x}: {before.hex()}")
                patched[off:off+4] = new
                if bytes(patched[off:off+4]) != new or bytes(patched).find(item["signature"]) != -1:
                    raise RuntimeError(f"{path} {item['name']}: verificación del parche falló")
                report["patches"].append({
                    "path": path, "abi": spec["abi"], "function": item["name"],
                    "file_offset": hex(off), "before": old.hex(), "after": new.hex(),
                    "verified": True,
                })
            replacements[path] = bytes(patched)

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
            raise RuntimeError(f"APK ZIP corrupta en {bad}")
        for path, spec in TARGETS.items():
            data = check.read(path)
            for item in spec["patches"]:
                if bytes.fromhex(item["new"]) not in data:
                    raise RuntimeError(f"Parche no presente tras reabrir APK: {path} {item['name']}")
        for item in report["pak_integrity"]:
            if sha256(check.read(item["path"])) != item["sha256"]:
                raise RuntimeError(f"PAK modificado: {item['path']}")

    report["patched_unsigned_apk_sha256"] = sha256(args.output_apk.read_bytes())
    report["patched_unsigned_apk_size"] = args.output_apk.stat().st_size
    report["zip_integrity"] = "passed"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
