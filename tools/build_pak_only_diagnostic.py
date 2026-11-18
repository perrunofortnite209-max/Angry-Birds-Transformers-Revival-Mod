#!/usr/bin/env python3
"""Build a PAK-only diagnostic APK without Apktool or Android resource rebuilds."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys, tempfile, zipfile
from pathlib import Path

def load(path):
    spec=importlib.util.spec_from_file_location("visual_builder",path)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod

def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apk",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--repo",type=Path,default=Path("."))
    ap.add_argument("--only",choices=("settings","features","vfx","both"),default="both")
    a=ap.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
    builder=load(a.repo/"tools/build_visual_test_apk.py")
    include=("settings","features","vfx") if a.only=="both" else (a.only,)
    report={"type":f"PAK-only diagnostic ({a.only})","selected_patch":a.only,"apktool_used":False,"manifest_rebuilt":False,
            "dex_rebuilt":False,"icon_changed":False,"welcome_dialog_added":False,
            "gameplay_fps_graphics_code_changed":False,"particle_vfx_thresholds_tuned":a.only in ("vfx","both"),"resources":[],"changed_zip_entries":[]}
    with tempfile.TemporaryDirectory(prefix="abt-pak-only-") as td:
        intermediate=Path(td)/"patched-with-old-signature.apk"
        builder.patch_paks(a.apk,intermediate,a.repo.resolve(),report,include=include)
        with zipfile.ZipFile(a.apk,"r") as original, zipfile.ZipFile(intermediate,"r") as patched, zipfile.ZipFile(a.out,"w") as output:
            original_names=set(original.namelist())
            for info in patched.infolist():
                upper=info.filename.upper()
                if upper.startswith("META-INF/") and (upper.endswith((".RSA",".DSA",".EC",".SF")) or upper=="META-INF/MANIFEST.MF"):
                    continue
                data=patched.read(info.filename)
                if info.filename in original_names:
                    old=original.read(info.filename)
                    if sha(data)!=sha(old):
                        report["changed_zip_entries"].append({"entry":info.filename,"before_sha256":sha(old),"after_sha256":sha(data)})
                output.writestr(info,data)
    if not report["changed_zip_entries"]:
        raise RuntimeError("No se detectaron cambios en entradas del APK")
    expected={x["entry"] for x in report["changed_zip_entries"]}
    if any(not x.endswith(".pak") for x in expected):
        raise RuntimeError(f"Se modificaron entradas ajenas a PAK: {sorted(expected)}")
    with zipfile.ZipFile(a.out,"r") as check:
        bad=check.testzip()
        if bad: raise RuntimeError(f"ZIP dañado: {bad}")
        for entry in expected:
            if check.read(entry)==b"": raise RuntimeError(f"PAK vacío: {entry}")
    report["only_pak_entries_changed"]=sorted(expected)
    report["all_non_pak_payloads_preserved"]=True
    report["output"]=a.out.name
    a.out.with_suffix(".report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"PAK-ONLY BUILD FAILED: {e}",file=sys.stderr); raise SystemExit(2)
