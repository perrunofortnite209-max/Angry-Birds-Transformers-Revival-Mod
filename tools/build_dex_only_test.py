#!/usr/bin/env python3
"""Patch only DEX code and transplant it into the untouched original APK container."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, subprocess, sys, tempfile, zipfile
from pathlib import Path

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def run(args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)

def load_welcome_helper(repo: Path):
    path = repo / "tools/build_visual_test_apk.py"
    spec = importlib.util.spec_from_file_location("abt_visual_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("No se pudo cargar el parche de bienvenida")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.patch_welcome

def is_dex(name: str) -> bool:
    base = Path(name).name
    return base == "classes.dex" or (base.startswith("classes") and base.endswith(".dex"))

def is_signature(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("META-INF/") and (
        upper.endswith((".RSA", ".DSA", ".EC", ".SF")) or
        upper in ("META-INF/MANIFEST.MF", "META-INF/SIG-BLOCK.RSA")
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path("."))
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    report = {"method": "DEX-only transplant", "pak_modified": False,
              "manifest_modified": False, "resources_modified": False,
              "native_libraries_modified": False}
    patch_welcome = load_welcome_helper(args.repo.resolve())
    with tempfile.TemporaryDirectory(prefix="abt-dex-only-") as td:
        td = Path(td)
        decoded, rebuilt = td / "decoded", td / "rebuilt.apk"
        run(["apktool", "d", "-f", str(args.apk), "-o", str(decoded)])
        patch_welcome(decoded, report)
        run(["apktool", "b", "--use-aapt2", str(decoded), "-o", str(rebuilt)])
        with zipfile.ZipFile(rebuilt) as zrebuilt:
            new_dex = {n: zrebuilt.read(n) for n in zrebuilt.namelist() if is_dex(n)}
        if not new_dex:
            raise RuntimeError("Apktool no generó archivos DEX")
        with zipfile.ZipFile(args.apk) as original:
            old_dex = {n for n in original.namelist() if is_dex(n)}
            if old_dex != set(new_dex):
                raise RuntimeError(f"El conjunto DEX cambió: original={sorted(old_dex)} rebuild={sorted(new_dex)}")
            before = {n: sha(original.read(n)) for n in original.namelist() if not is_dex(n) and not is_signature(n)}
            with zipfile.ZipFile(args.out, "w") as output:
                for info in original.infolist():
                    name = info.filename
                    if is_signature(name):
                        continue
                    payload = new_dex[name] if is_dex(name) else original.read(name)
                    output.writestr(info, payload)
        with zipfile.ZipFile(args.out) as check:
            bad = check.testzip()
            if bad:
                raise RuntimeError(f"ZIP corrupto: {bad}")
            after = {n: sha(check.read(n)) for n in check.namelist() if not is_dex(n) and not is_signature(n)}
            if before != after:
                changed = [n for n in before if before[n] != after.get(n)]
                raise RuntimeError(f"Entradas ajenas a DEX cambiaron: {changed[:20]}")
            report["unchanged_entries"] = len(before)
            report["dex_entries_replaced"] = sorted(new_dex)
            report["all_non_dex_entries_sha256_identical"] = True
            report["apk_zip_test"] = "passed"
    report["output_sha256"] = sha(args.out.read_bytes())
    report["output_size"] = args.out.stat().st_size
    report_path = args.out.parent / "ABT-DEX-ONLY-DIAGNOSTIC.report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"DEX-ONLY BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
