#!/usr/bin/env python3
"""Build a visual-only Angry Birds Transformers Revival Mod test APK."""
from __future__ import annotations
import argparse, importlib.util, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"
WELCOME = ("¡Bienvenido a Angry Birds Transformers: Revival Mod! Una versión renovada "
           "para dispositivos Android actuales, con controles de FPS y opciones de "
           "rendimiento. ¡Prepárate para volver a la batalla!")

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError(f"No se pudo cargar {path}")
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod

def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(list(map(str, cmd)), check=True)

def patch_settings(xml):
    root = ET.fromstring(xml)
    button = root.find(".//CPanelWindow_FeatureConfig")
    if button is None: raise RuntimeError("No se encontró CPanelWindow_FeatureConfig en uisettingsscreen.xml")
    button.set("visibility", "visible")
    label = button.find(".//CTextLabel_Feature")
    if label is None: raise RuntimeError("No se encontró CTextLabel_Feature")
    label.set("text", "MOD SETTINGS"); label.set("scaleToFit", "true")
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)

def patch_features(xml):
    root = ET.fromstring(xml)
    if root.tag != "FeatureConfig": raise RuntimeError(f"Raíz FeatureConfig inesperada: {root.tag}")
    rows = [
        ("ABT_Visual_FPS", "FPS LIMIT (PREVIEW)"),
        ("ABT_Visual_Graphics", "GRAPHICS PATCH (PREVIEW)"),
        ("ABT_Visual_VSync", "V-SYNC (PREVIEW)"),
    ]
    existing = {x.get("feature") for x in root.findall("Setting")}
    for feature, title in rows:
        if feature not in existing:
            ET.SubElement(root, "Setting", {"feature": feature, "enabled": "false",
                                            "onScreen": "true", "displayName": title})
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)

def patch_paks(apk, output, root, report):
    kpx = load_module(root / "tools/xgs_kpx_v2.py", "xgs_kpx_v2")
    codec = load_module(root / "tools/xox2_codec.py", "xox2_codec")
    with zipfile.ZipFile(apk) as zin:
        paks = [n for n in zin.namelist() if n.lower().endswith(".pak")]
        found = {"settings": [], "features": []}
        for name in paks:
            blob = zin.read(name)
            try: meta = kpx.parse(blob)
            except Exception: continue
            for e in meta["entries"]:
                low = e.name.replace("\\", "/").lower()
                if low.endswith("uisettingsscreen.xml"):
                    found["settings"].append((name, blob, meta, e))
                if low.endswith("featureconfig.xml") and "uifeatureconfigscreen" not in low:
                    found["features"].append((name, blob, meta, e))
        for kind in found:
            if len(found[kind]) != 1:
                raise RuntimeError(f"Recurso {kind}: se esperaba 1 coincidencia, hay {[(x[0],x[3].name) for x in found[kind]]}")
        replacements = {}
        for kind, patcher in (("settings", patch_settings), ("features", patch_features)):
            pak, blob, meta, entry = found[kind][0]
            original = kpx.unpack_entry(blob, meta, entry)
            xml = codec.decode(original); ET.fromstring(xml)
            encoded = codec.encode(patcher(xml))
            ET.fromstring(codec.decode(encoded))
            rebuilt = kpx.rebuild(blob, meta, entry.name, encoded)
            kpx.verify(blob, rebuilt, meta, entry.name, encoded)
            replacements[pak] = rebuilt
            report["resources"].append({"pak": pak, "entry": entry.name,
                "xox2_roundtrip": True, "kpx_validation": True,
                "purpose": "visible settings entry" if kind == "settings" else "inert preview toggles"})
        with zipfile.ZipFile(output, "w") as zout:
            for info in zin.infolist():
                zout.writestr(info, replacements.get(info.filename, zin.read(info.filename)))

def patch_icon(decoded, icon_file):
    from PIL import Image, ImageOps
    src = Image.open(icon_file).convert("RGBA")
    canvas = Image.new("RGBA", (432,432), (16,24,39,255))
    fitted = ImageOps.contain(src, (400,400), method=Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, ((432-fitted.width)//2, (432-fitted.height)//2))
    res = decoded / "res"
    (res/"drawable-nodpi").mkdir(parents=True, exist_ok=True)
    canvas.save(res/"drawable-nodpi/abt_icon_foreground.png")
    for folder, size in {"mipmap-mdpi":48,"mipmap-hdpi":72,"mipmap-xhdpi":96,
                         "mipmap-xxhdpi":144,"mipmap-xxxhdpi":192}.items():
        d=res/folder; d.mkdir(parents=True, exist_ok=True)
        canvas.resize((size,size),Image.Resampling.LANCZOS).save(d/"ic_launcher.png")
        canvas.resize((size,size),Image.Resampling.LANCZOS).save(d/"ic_launcher_round.png")
    anydpi=res/"mipmap-anydpi-v26"; anydpi.mkdir(parents=True,exist_ok=True)
    adaptive='''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/abt_icon_bg"/>
    <foreground android:drawable="@drawable/abt_icon_foreground"/>
</adaptive-icon>'''
    (anydpi/"ic_launcher.xml").write_text(adaptive,encoding="utf-8")
    (anydpi/"ic_launcher_round.xml").write_text(adaptive,encoding="utf-8")
    values=res/"values"; values.mkdir(parents=True,exist_ok=True)
    (values/"abt_icon_colors.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources><color name="abt_icon_bg">#101827</color></resources>\n',
        encoding="utf-8")
    manifest=decoded/"AndroidManifest.xml"
    tree=ET.parse(manifest); app=tree.getroot().find("application")
    if app is None: raise RuntimeError("No existe application en AndroidManifest.xml")
    app.set(ANDROID+"icon","@mipmap/ic_launcher")
    app.set(ANDROID+"roundIcon","@mipmap/ic_launcher_round")
    tree.write(manifest,encoding="utf-8",xml_declaration=True)

def patch_welcome(decoded, report):
    descriptor="Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;"
    hits=[]
    for p in decoded.glob("smali*/**/*.smali"):
        try: s=p.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        if re.search(r"^\.class\b.*"+re.escape(descriptor),s,re.M): hits.append((p,s))
    if len(hits)!=1: raise RuntimeError(f"Activity Rovio no encontrada de forma única: {len(hits)}")
    path, source=hits[0]
    if "showRevivalWelcomeOnce()V" in source: raise RuntimeError("Helper de bienvenida ya presente")
    pattern=re.compile(r"(?ms)^\.method[^\n]*\bonCreate\(Landroid/os/Bundle;\)V\b.*?^\.end method")
    match=pattern.search(source)
    if not match: raise RuntimeError("No se encontró onCreate(Bundle) en la Activity principal")
    method=match.group(0); returns=list(re.finditer(r"(?m)^\s*return-void\s*$",method))
    if not returns: raise RuntimeError("No se encontró return-void en onCreate")
    at=returns[-1].start()
    method=method[:at]+f"    invoke-direct {{p0}}, {descriptor}->showRevivalWelcomeOnce()V\n"+method[at:]
    source=source[:match.start()]+method+source[match.end():]
    helper=r'''
.method private showRevivalWelcomeOnce()V
    .locals 5
    const-string v0, "abt_revival_mod"
    const/4 v1, 0x0
    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v0
    const-string v1, "welcome_shown"
    const/4 v2, 0x0
    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v2
    if-nez v2, :welcome_done
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    const/4 v2, 0x1
    invoke-interface {v3, v1, v2}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    invoke-interface {v3}, Landroid/content/SharedPreferences$Editor;->apply()V
    new-instance v4, Landroid/app/AlertDialog$Builder;
    invoke-direct {v4, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v1, "Angry Birds Transformers: Revival Mod"
    invoke-virtual {v4, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const-string v1, "¡Bienvenido a Angry Birds Transformers: Revival Mod! Una versión renovada para dispositivos Android actuales, con controles de FPS y opciones de rendimiento. ¡Prepárate para volver a la batalla!"
    invoke-virtual {v4, v1}, Landroid/app/AlertDialog$Builder;->setMessage(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const-string v1, "ENTENDIDO"
    const/4 v2, 0x0
    invoke-virtual {v4, v1, v2}, Landroid/app/AlertDialog$Builder;->setPositiveButton(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v4}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    :welcome_done
    return-void
.end method
'''
    path.write_text(source+"\n"+helper,encoding="utf-8")
    report["welcome"]={"first_launch_only":True,"dismissible":True,"method":"Android AlertDialog + SharedPreferences"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apk",type=Path,required=True); ap.add_argument("--icon",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True); ap.add_argument("--repo",type=Path,default=Path("."))
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    report={"type":"visual-only test","gameplay_fps_graphics_code_changed":False,
            "preview_toggles_inert":True,"resources":[]}
    with tempfile.TemporaryDirectory(prefix="abt-visual-") as td:
        td=Path(td); patched=td/"assets-patched.apk"; decoded=td/"decoded"
        patch_paks(a.apk,patched,a.repo.resolve(),report)
        run(["apktool","d","-f",str(patched),"-o",str(decoded)])
        patch_icon(decoded,a.icon); patch_welcome(decoded,report)
        unsigned=a.out/"Angry-Birds-Transformers-Revival-Mod-VISUAL-TEST-unsigned.apk"
        run(["apktool","b","--use-aapt2",str(decoded),"-o",str(unsigned)])
    report["icon"]={"launcher":True,"adaptive":True,"round":True}
    report["output"]=unsigned.name
    (a.out/"visual-test-report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"VISUAL TEST BUILD FAILED: {exc}",file=sys.stderr); raise SystemExit(2)
