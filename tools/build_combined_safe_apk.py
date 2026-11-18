#!/usr/bin/env python3
"""Build a safe combined APK without a forced native FPS cap.
All original game libraries, PAKs and unrelated APK entries remain byte-identical; only DEX, manifest and launcher icons are updated.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXPECTED = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
# Keep original engine FPS constants unchanged.

def sha(b): return hashlib.sha256(b).hexdigest()
def run(cmd): print("+", " ".join(map(str,cmd)), flush=True); subprocess.run(list(map(str,cmd)),check=True)
def load_patch(repo):
 p=repo/"tools/build_visual_test_apk.py"
 spec=importlib.util.spec_from_file_location("abt_visual_helpers",p)
 mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
 return mod.patch_welcome
def load_controls(repo):
 p=repo/"tools/patch_revival_controls.py"
 spec=importlib.util.spec_from_file_location("abt_revival_controls",p)
 mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
 return mod.patch
ICON_ENTRIES = {
 "res/aH.png",   # default
 "res/4W.png",   # ldpi
 "res/uI.png",   # mdpi
 "res/5J.png",   # hdpi
 "res/_X.png",   # xhdpi
 "res/pr.png",   # xxhdpi
 "res/ad.png",   # xxxhdpi
}
def make_icon_payload(source_png, width, height):
 from PIL import Image
 src=Image.open(source_png).convert('RGBA')
 canvas=Image.new('RGBA',(width,height),(0,0,0,255))
 # Fit the complete artwork inside the original launcher-icon dimensions; never crop or zoom.
 src.thumbnail((width,height),Image.Resampling.LANCZOS)
 canvas.alpha_composite(src,((width-src.width)//2,(height-src.height)//2))
 out=io.BytesIO(); canvas.save(out,format='PNG',optimize=False); return out.getvalue()
def is_icon(n):
 return n in ICON_ENTRIES
def is_dex(n):
 x=Path(n).name
 return x=="classes.dex" or (x.startswith("classes") and x.endswith(".dex"))
def is_sig(n):
 u=n.upper()
 return u.startswith("META-INF/") and (u.endswith((".RSA",".DSA",".EC",".SF")) or u=="META-INF/MANIFEST.MF")
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--apk",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); ap.add_argument("--repo",type=Path,default=Path(".")); ap.add_argument("--icon",type=Path,required=True); ap.add_argument("--native-arm64",type=Path,required=True); ap.add_argument("--native-armv7",type=Path,required=True)
 a=ap.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
 src=a.apk.read_bytes()
 if sha(src)!=EXPECTED: raise RuntimeError("El APK de entrada no coincide con el original 2.42.0 analizado")
 report={"method":"DEX transplant + runtime FPS/graphics JNI bridge","target_fps":"user-selectable","pak_modified":False,"manifest_modified":True,"resources_modified":True,"icon_safe_scale":1.0,"icon_entries":[],"welcome_first_launch":True,"fps_patches":[],"native_fps_constants_modified":False,"fps_policy":"original engine defaults until a user-selected runtime cap is applied"}
 welcome=load_patch(a.repo.resolve())
 controls=load_controls(a.repo.resolve())
 native_payloads={"lib/arm64-v8a/libabtmod.so":a.native_arm64.read_bytes(),"lib/armeabi-v7a/libabtmod.so":a.native_armv7.read_bytes()}
 with tempfile.TemporaryDirectory(prefix="abt-combined-") as td:
  td=Path(td); decoded=td/"decoded"; rebuilt=td/"rebuilt.apk"
  run(["apktool","d","-f",str(a.apk),"-o",str(decoded)])
  welcome(decoded,report)
  controls(decoded,report)
  manifest_path=decoded/"AndroidManifest.xml"
  tree=ET.parse(manifest_path); root=tree.getroot()
  android="{http://schemas.android.com/apk/res/android}"
  app=root.find("application")
  if app is None: raise RuntimeError("AndroidManifest.xml no contiene application")
  old_code=int(app.get(android+"versionCode","24200"))
  run_number=int(os.environ.get("GITHUB_RUN_NUMBER","1"))
  run_attempt=int(os.environ.get("GITHUB_RUN_ATTEMPT","1"))
  new_code=max(old_code+1,24200+run_number*100+run_attempt)
  app.set(android+"versionCode",str(new_code))
  tree.write(manifest_path,encoding="utf-8",xml_declaration=True)
  report["version_code"]={"previous":old_code,"new":new_code,"update_in_place":True}
  run(["apktool","b","--use-aapt2",str(decoded),"-o",str(rebuilt)])
  with zipfile.ZipFile(rebuilt) as z:
   dex={n:z.read(n) for n in z.namelist() if is_dex(n)}
   manifest_payload=z.read("AndroidManifest.xml")
  with zipfile.ZipFile(a.apk) as original:
   olddex={n for n in original.namelist() if is_dex(n)}
   if olddex!=set(dex): raise RuntimeError(f"Conjunto DEX distinto: {olddex} vs {set(dex)}")
   names=original.namelist()
   icon_names=[n for n in names if is_icon(n)]
   if len(icon_names)!=7:
    candidates=[n for n in names if "app_icon" in n.lower() or ("drawable" in n.lower() and n.lower().endswith((".png",".webp")))]
    raise RuntimeError(f"Expected 7 launcher PNGs, found {len(icon_names)}: {icon_names}; nearby resource entries: {candidates[:80]}")
   before={n:sha(original.read(n)) for n in names if n!="AndroidManifest.xml" and not is_dex(n) and not is_icon(n) and not is_sig(n)}
   with zipfile.ZipFile(a.out,"w") as out:
    for info in original.infolist():
     n=info.filename
     if is_sig(n): continue
     payload=dex[n] if is_dex(n) else manifest_payload if n=="AndroidManifest.xml" else original.read(n)
     if is_icon(n):
      from PIL import Image
      with Image.open(io.BytesIO(original.read(n))) as old_icon: w,h=old_icon.size
      payload=make_icon_payload(a.icon,w,h)
      report["icon_entries"].append({"path":n,"width":w,"height":h,"verified":True})
     out.writestr(info,payload)
    for native_name,native_data in native_payloads.items():
     out.writestr(native_name,native_data,compress_type=zipfile.ZIP_STORED)
   report["native_bridge_entries"]={name:{"size":len(data),"sha256":sha(data)} for name,data in native_payloads.items()}
  with zipfile.ZipFile(a.out) as check:
   bad=check.testzip()
   if bad: raise RuntimeError(f"ZIP dañado: {bad}")
   after={n:sha(check.read(n)) for n in check.namelist() if n!="AndroidManifest.xml" and not is_dex(n) and n not in native_payloads and not is_icon(n) and not is_sig(n)}
   if before!=after: raise RuntimeError("Cambió una entrada ajena a DEX/libABBS")
   for native_name,native_data in native_payloads.items():
    if check.read(native_name)!=native_data: raise RuntimeError(f"Native bridge mismatch: {native_name}")
   report["unchanged_entries"]=len(before); report["pak_and_unrelated_entries_sha256_identical"]=True; report["only_resource_changes_are_launcher_icon_pngs"]=True; report["apk_zip_test"]="passed"
 report["output_sha256"]=sha(a.out.read_bytes()); report["output_size"]=a.out.stat().st_size
 rp=a.out.parent/"ABT-REVIVAL-COMBINED.report.json"; rp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__":
 try: main()
 except Exception as e: print(f"BUILD FAILED: {e}",file=sys.stderr); raise SystemExit(2)
