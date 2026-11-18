#!/usr/bin/env python3
"""Build a safe combined APK: welcome DEX patch + guarded native 144 FPS patch.
All PAKs, manifest, resources and unrelated APK entries remain byte-identical.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

EXPECTED = "ace138aac9456b81432a59b0f1ee9b475d20b0d5cffd4664fc5e4b74d0772013"
TARGETS = {
 "lib/arm64-v8a/libABBS.so": [
  ("CApp::GetDesiredFramerate",
   "4830009008ed42f9080140f9080100b4083d40f9c80000b408bd42b91f0900716100005480078052c0035fd6e0031f2ac0035fd6",
   0x24, "80078052", "00128052"),
  ("CDeviceConfig::GetDesiredFramerate",
   "fd7bbfa9fd0300918ee4ff97a83200908907805208b548b91f010071c80380522801881a1f0000710001801afd7bc1a8c0035fd6",
   0x1c, "c8038052", "08128052")],
 "lib/armeabi-v7a/libABBS.so": [
  ("CApp::GetDesiredFramerate",
   "38009fe500009fe7001090e50000a0e3000051e31eff2f01500091e5000050e30400000a041290e53c00a0e3020051e30000a0131eff2fe10000a0e31eff2fe1",
   0x28, "3c00a0e3", "9000a0e3"),
  ("CDeviceConfig::GetDesiredFramerate",
   "00482de976e3ffeb1c109fe51e20a0e301108fe0041091e5000051e33c200003000050e30200a0010088bde8",
   0x0c, "1e20a0e3", "9002a0e3")]
}
def sha(b): return hashlib.sha256(b).hexdigest()
def run(cmd): print("+", " ".join(map(str,cmd)), flush=True); subprocess.run(list(map(str,cmd)),check=True)
def load_patch(repo):
 p=repo/"tools/build_visual_test_apk.py"
 spec=importlib.util.spec_from_file_location("abt_visual_helpers",p)
 mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
 return mod.patch_welcome
def patch_lib(path, data, report):
 b=bytearray(data)
 for fn,sighex,off,oldhex,newhex in TARGETS[path]:
  sig=bytes.fromhex(sighex); hits=[]; start=0
  while True:
   pos=b.find(sig,start)
   if pos<0: break
   hits.append(pos); start=pos+1
  if len(hits)!=1: raise RuntimeError(f"{path}: firma de {fn} no única ({len(hits)})")
  at=hits[0]+off; old=bytes.fromhex(oldhex); new=bytes.fromhex(newhex)
  if bytes(b[at:at+4])!=old: raise RuntimeError(f"{path}: bytes inesperados en {fn}: {bytes(b[at:at+4]).hex()}")
  b[at:at+4]=new
  if bytes(b[at:at+4])!=new: raise RuntimeError(f"Verificación fallida: {fn}")
  report["fps_patches"].append({"library":path,"function":fn,"offset":hex(at),"before":oldhex,"after":newhex,"verified":True})
 return bytes(b)
def is_dex(n):
 x=Path(n).name
 return x=="classes.dex" or (x.startswith("classes") and x.endswith(".dex"))
def is_sig(n):
 u=n.upper()
 return u.startswith("META-INF/") and (u.endswith((".RSA",".DSA",".EC",".SF")) or u=="META-INF/MANIFEST.MF")
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--apk",type=Path,required=True); ap.add_argument("--out",type=Path,required=True); ap.add_argument("--repo",type=Path,default=Path("."))
 a=ap.parse_args(); a.out.parent.mkdir(parents=True,exist_ok=True)
 src=a.apk.read_bytes()
 if sha(src)!=EXPECTED: raise RuntimeError("El APK de entrada no coincide con el original 2.42.0 analizado")
 report={"method":"DEX transplant + guarded native FPS patch","target_fps":144,"pak_modified":False,"manifest_modified":False,"resources_modified":False,"welcome_first_launch":True,"fps_patches":[]}
 welcome=load_patch(a.repo.resolve())
 with tempfile.TemporaryDirectory(prefix="abt-combined-") as td:
  td=Path(td); decoded=td/"decoded"; rebuilt=td/"rebuilt.apk"
  run(["apktool","d","-f",str(a.apk),"-o",str(decoded)])
  welcome(decoded,report)
  run(["apktool","b","--use-aapt2",str(decoded),"-o",str(rebuilt)])
  with zipfile.ZipFile(rebuilt) as z: dex={n:z.read(n) for n in z.namelist() if is_dex(n)}
  with zipfile.ZipFile(a.apk) as original:
   olddex={n for n in original.namelist() if is_dex(n)}
   if olddex!=set(dex): raise RuntimeError(f"Conjunto DEX distinto: {olddex} vs {set(dex)}")
   names=original.namelist()
   if any(names.count(p)!=1 for p in TARGETS): raise RuntimeError("Falta una biblioteca nativa o está duplicada")
   replacements={p:patch_lib(p,original.read(p),report) for p in TARGETS}
   before={n:sha(original.read(n)) for n in names if not is_dex(n) and n not in TARGETS and not is_sig(n)}
   with zipfile.ZipFile(a.out,"w") as out:
    for info in original.infolist():
     n=info.filename
     if is_sig(n): continue
     payload=dex[n] if is_dex(n) else replacements[n] if n in replacements else original.read(n)
     out.writestr(info,payload)
  with zipfile.ZipFile(a.out) as check:
   bad=check.testzip()
   if bad: raise RuntimeError(f"ZIP dañado: {bad}")
   after={n:sha(check.read(n)) for n in check.namelist() if not is_dex(n) and n not in TARGETS and not is_sig(n)}
   if before!=after: raise RuntimeError("Cambió una entrada ajena a DEX/libABBS")
   for p in TARGETS:
    for fn,sig,off,old,new in TARGETS[p]:
     entry=check.read(p)
     # Each target instruction was verified before writing; report includes exact resulting bytes.
     match=next(x for x in report["fps_patches"] if x["library"]==p and x["function"]==fn)
     if entry[int(match["offset"],16):int(match["offset"],16)+4]!=bytes.fromhex(new): raise RuntimeError(f"FPS patch no persistió: {fn}")
   report["unchanged_entries"]=len(before); report["pak_and_unrelated_entries_sha256_identical"]=True; report["apk_zip_test"]="passed"
 report["output_sha256"]=sha(a.out.read_bytes()); report["output_size"]=a.out.stat().st_size
 rp=a.out.parent/"ABT-REVIVAL-COMBINED.report.json"; rp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=="__main__":
 try: main()
 except Exception as e: print(f"BUILD FAILED: {e}",file=sys.stderr); raise SystemExit(2)
