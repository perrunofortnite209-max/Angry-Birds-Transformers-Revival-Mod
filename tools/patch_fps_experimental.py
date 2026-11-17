#!/usr/bin/env python3
"""Experimental, guarded FPS patch for Angry Birds Transformers 2.42.0.

Only changes the exact immediate in CApp::GetDesiredFramerate() for ARM64/ARM32.
It refuses to patch if the APK or instruction bytes differ from the analyzed build.
"""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path
from elftools.elf.elffile import ELFFile

EXPECTED_APK_SHA256 = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
PATCHES = {
    "lib/arm64-v8a/libABBS.so": {
        "abi": "AArch64",
        "vaddr": 0x007E6644,
        "old": bytes.fromhex("80078052"),  # mov w0, #0x3c (60)
        "new": bytes.fromhex("00128052"),  # mov w0, #0x90 (144)
        "machine": "EM_AARCH64",
    },
    "lib/armeabi-v7a/libABBS.so": {
        "abi": "ARM32",
        "vaddr": 0x0051DEBC,
        "old": bytes.fromhex("3c00a0e3"),  # mov r0, #0x3c (60)
        "new": bytes.fromhex("9000a0e3"),  # mov r0, #0x90 (144)
        "machine": "EM_ARM",
    },
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def vaddr_to_offset(blob: bytes, vaddr: int, expected_machine: str) -> int:
    elf = ELFFile(io.BytesIO(blob))
    machine = elf.header["e_machine"]
    if machine != expected_machine:
        raise RuntimeError(f"Arquitectura incorrecta: {machine}, esperada {expected_machine}")
    for seg in elf.iter_segments():
        if seg["p_type"] == "PT_LOAD":
            start = int(seg["p_vaddr"])
            size = int(seg["p_filesz"])
            if start <= vaddr and vaddr + 4 <= start + size:
                return int(seg["p_offset"]) + (vaddr - start)
    raise RuntimeError(f"No se pudo mapear VA 0x{vaddr:x} a bytes del ELF")

def patch_library(blob: bytes, spec: dict) -> tuple[bytes, dict]:
    offset = vaddr_to_offset(blob, spec["vaddr"], spec["machine"])
    actual = blob[offset:offset+4]
    if actual != spec["old"]:
        raise RuntimeError(
            f"{spec['abi']}: bytes inesperados en VA 0x{spec['vaddr']:x} "
            f"(offset 0x{offset:x}): {actual.hex()} != {spec['old'].hex()}; "
            "se aborta para evitar corromper la biblioteca"
        )
    out = bytearray(blob)
    out[offset:offset+4] = spec["new"]
    if bytes(out[offset:offset+4]) != spec["new"]:
        raise RuntimeError(f"{spec['abi']}: verificación posterior fallida")
    return bytes(out), {
        "abi": spec["abi"], "virtual_address": hex(spec["vaddr"]),
        "file_offset": hex(offset), "before": actual.hex(),
        "after": spec["new"].hex(), "library_sha256_before": sha256(blob),
        "library_sha256_after": sha256(bytes(out)),
    }

def is_old_signature_file(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("META-INF/") and (
        upper.endswith((".RSA", ".DSA", ".EC", ".SF")) or
        upper == "META-INF/MANIFEST.MF"
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
        raise SystemExit(f"APK SHA-256 no coincide ({digest}); solo se parchea el original analizado.")
    report = {"apk_sha256_original": digest, "patches": [], "removed_old_signatures": []}
    with zipfile.ZipFile(io.BytesIO(source), "r") as zin:
        names = zin.namelist()
        for name in PATCHES:
            if names.count(name) != 1:
                raise SystemExit(f"Se esperaba una sola entrada {name}; encontradas {names.count(name)}")
        replacements = {}
        for name, spec in PATCHES.items():
            patched, item = patch_library(zin.read(name), spec)
            replacements[name] = patched
            report["patches"].append({"path": name, **item})
        out_buffer = io.BytesIO()
        with zipfile.ZipFile(out_buffer, "w") as zout:
            for info in zin.infolist():
                if is_old_signature_file(info.filename):
                    report["removed_old_signatures"].append(info.filename)
                    continue
                payload = replacements.get(info.filename)
                if payload is None:
                    payload = zin.read(info.filename)
                # Preserve entry metadata and compression method; zipalign runs after this script.
                zout.writestr(info, payload)
    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(out_buffer.getvalue())
    report["unsigned_patched_apk_sha256"] = sha256(args.output_apk.read_bytes())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
