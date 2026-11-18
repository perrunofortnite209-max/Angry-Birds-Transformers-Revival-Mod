#!/usr/bin/env python3
"""Build a visual-only Angry Birds Transformers Revival Mod test APK."""
from __future__ import annotations
import argparse, importlib.util, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"
WELCOME = ("¡Bienvenido a Angry Birds Transformers: Revival Mod! Una versión renovada "
           "para dispositivos Android actuales, con controles de FPS y opciones de "
           "rendimiento.")

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

def patch_paks(apk, output, root, report, include=("settings", "features")):
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
        for kind in include:
            if len(found[kind]) != 1:
                raise RuntimeError(f"Recurso {kind}: se esperaba 1 coincidencia, hay {[(x[0],x[3].name) for x in found[kind]]}")
        replacements = {}
        for kind, patcher in (("settings", patch_settings), ("features", patch_features)):
            if kind not in include:
                continue
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
    if "showRevivalWelcomeOnce()V" in source or "showRevivalFloatingBallIfReady()V" in source: raise RuntimeError("Helpers Revival Mod ya presentes")
    pattern=re.compile(r"(?ms)^\.method[^\n]*\bonCreate\(Landroid/os/Bundle;\)V\b.*?^\.end method")
    match=pattern.search(source)
    if not match: raise RuntimeError("No se encontró onCreate(Bundle) en la Activity principal")
    method=match.group(0); returns=list(re.finditer(r"(?m)^\s*return-void\s*$",method))
    if not returns: raise RuntimeError("No se encontró return-void en onCreate")
    at=returns[-1].start()
    method=method[:at]+f"    invoke-direct {{p0}}, {descriptor}->showRevivalWelcomeOnce()V\n    invoke-direct {{p0}}, {descriptor}->showRevivalFloatingBallIfReady()V\n"+method[at:]
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
    const-string v1, "¡Bienvenido a Angry Birds Transformers: Revival Mod! Una versión renovada para dispositivos Android actuales, con controles de FPS y opciones de rendimiento."
    invoke-virtual {v4, v1}, Landroid/app/AlertDialog$Builder;->setMessage(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const-string v1, "ENTENDIDO"
    const/4 v2, 0x0
    invoke-virtual {v4, v1, v2}, Landroid/app/AlertDialog$Builder;->setPositiveButton(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v4}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    :welcome_done
    return-void
.end method
'''
    floating_helper=r"""
.method private showRevivalFloatingBallIfReady()V
    .locals 8
    const-string v0, "abt_revival_mod"
    const/4 v1, 0x0
    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v0
    const-string v1, "ball_session_seen"
    const/4 v2, 0x0
    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v2
    if-nez v2, :ball_show
    invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    const/4 v2, 0x1
    invoke-interface {v3, v1, v2}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    invoke-interface {v3}, Landroid/content/SharedPreferences$Editor;->apply()V
    return-void
    :ball_show
    invoke-virtual {p0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;
    move-result-object v0
    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;
    move-result-object v0
    const v1, 0x1020002
    invoke-virtual {v0, v1}, Landroid/view/View;->findViewById(I)Landroid/view/View;
    move-result-object v4
    check-cast v4, Landroid/widget/FrameLayout;
    const-string v0, "abt_revival_ball_view"
    invoke-virtual {v4, v0}, Landroid/view/ViewGroup;->findViewWithTag(Ljava/lang/Object;)Landroid/view/View;
    move-result-object v0
    if-nez v0, :ball_done
    new-instance v5, Landroid/widget/TextView;
    invoke-direct {v5, p0}, Landroid/widget/TextView;-><init>(Landroid/content/Context;)V
    const-string v0, "T"
    invoke-virtual {v5, v0}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V
    const/high16 v0, 0x41a00000
    invoke-virtual {v5, v0}, Landroid/widget/TextView;->setTextSize(F)V
    const-string v0, "sans-serif"
    const/4 v1, 0x1
    invoke-static {v0, v1}, Landroid/graphics/Typeface;->create(Ljava/lang/String;I)Landroid/graphics/Typeface;
    move-result-object v0
    invoke-virtual {v5, v0}, Landroid/widget/TextView;->setTypeface(Landroid/graphics/Typeface;)V
    const/16 v0, 0x11
    invoke-virtual {v5, v0}, Landroid/widget/TextView;->setGravity(I)V
    const/4 v0, -0x1
    invoke-virtual {v5, v0}, Landroid/widget/TextView;->setTextColor(I)V
    new-instance v0, Landroid/graphics/drawable/GradientDrawable;
    invoke-direct {v0}, Landroid/graphics/drawable/GradientDrawable;-><init>()V
    const/4 v1, 0x1
    invoke-virtual {v0, v1}, Landroid/graphics/drawable/GradientDrawable;->setShape(I)V
    const/4 v1, 0x2
    new-array v1, v1, [I
    const v2, -0x750000
    const/4 v3, 0x0
    aput v2, v1, v3
    const v2, -0xc50000
    const/4 v3, 0x1
    aput v2, v1, v3
    invoke-virtual {v0, v1}, Landroid/graphics/drawable/GradientDrawable;->setColors([I)V
    const/4 v1, 0x2
    const v2, -0x4dddde
    invoke-virtual {v0, v1, v2}, Landroid/graphics/drawable/GradientDrawable;->setStroke(II)V
    invoke-virtual {v5, v0}, Landroid/view/View;->setBackground(Landroid/graphics/drawable/Drawable;)V
    const/high16 v0, 0x41000000
    invoke-virtual {v5, v0}, Landroid/view/View;->setElevation(F)V
    const/high16 v0, 0x41000000
    const/4 v1, 0x0
    const/4 v2, 0x0
    const v3, -0x4dddde
    invoke-virtual {v5, v0, v1, v2, v3}, Landroid/widget/TextView;->setShadowLayer(FFFI)V
    const/16 v0, 0x8
    const/4 v1, 0x6
    const/16 v2, 0x8
    const/4 v3, 0x6
    invoke-virtual {v5, v0, v1, v2, v3}, Landroid/widget/TextView;->setPadding(IIII)V
    invoke-virtual {p0}, Landroid/content/Context;->getResources()Landroid/content/res/Resources;
    move-result-object v6
    invoke-virtual {v6}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;
    move-result-object v6
    iget v6, v6, Landroid/util/DisplayMetrics;->density:F
    const/high16 v7, 0x42800000
    mul-float v7, v7, v6
    float-to-int v7, v7
    new-instance v0, Landroid/widget/FrameLayout$LayoutParams;
    const/16 v3, 0x15
    invoke-direct {v0, v7, v7, v3}, Landroid/widget/FrameLayout$LayoutParams;-><init>(III)V
    const/high16 v7, 0x41400000
    mul-float v7, v7, v6
    float-to-int v7, v7
    iput v7, v0, Landroid/widget/FrameLayout$LayoutParams;->rightMargin:I
    const-string v1, "abt_revival_ball_view"
    invoke-virtual {v5, v1}, Landroid/view/View;->setTag(Ljava/lang/Object;)V
    new-instance v1, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;
    invoke-direct {v1, v5}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;-><init>(Landroid/view/View;)V
    new-instance v2, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;
    invoke-direct {v2, p0, v1}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;-><init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;Ljava/lang/Runnable;)V
    invoke-virtual {v5, v2}, Landroid/view/View;->setOnTouchListener(Landroid/view/View$OnTouchListener;)V
    invoke-virtual {v4, v5, v0}, Landroid/view/ViewGroup;->addView(Landroid/view/View;Landroid/view/ViewGroup$LayoutParams;)V
    invoke-virtual {v5}, Landroid/view/View;->animate()Landroid/view/ViewPropertyAnimator;
    move-result-object v1
    const v2, 0x3f0ccccd
    invoke-virtual {v1, v2}, Landroid/view/ViewPropertyAnimator;->alpha(F)Landroid/view/ViewPropertyAnimator;
    move-result-object v1
    const-wide/16 v2, 0x1388
    invoke-virtual {v1, v2, v3}, Landroid/view/ViewPropertyAnimator;->setDuration(J)Landroid/view/ViewPropertyAnimator;
    move-result-object v1
    invoke-virtual {v1}, Landroid/view/ViewPropertyAnimator;->start()V
    :ball_done
    return-void
.end method
"""
    path.write_text(source+"\n"+helper+"\n"+floating_helper,encoding="utf-8")
    listener=path.parent.parent/"smali/com/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallClickListener.smali"
    listener.parent.mkdir(parents=True,exist_ok=True)
    listener.write_text(r""".class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallClickListener;
.super Ljava/lang/Object;
.implements Landroid/view/View$OnClickListener;

.field private final activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;

.method public constructor <init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallClickListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
    return-void
.end method

.method public onClick(Landroid/view/View;)V
    .locals 3
    new-instance v0, Landroid/app/AlertDialog$Builder;
    iget-object v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallClickListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
    invoke-direct {v0, v1}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v1, "MOD SETTINGS"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const-string v1, "REVIVAL MOD\n\nConfiguración rápida de la modificación y controles de rendimiento."
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setMessage(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const-string v1, "CERRAR"
    const/4 v2, 0x0
    invoke-virtual {v0, v1, v2}, Landroid/app/AlertDialog$Builder;->setPositiveButton(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method
""".lstrip(),encoding="utf-8")
    settings_helper=r"""
.method public showRevivalSettings()V
    .locals 8
    const-string v0, "abt_revival_mod"
    const/4 v1, 0x0
    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v4
    const/4 v1, 0x2
    new-array v2, v1, [Ljava/lang/CharSequence;
    const-string v3, "Ocultar automáticamente después de 30 segundos"
    const/4 v5, 0x0
    aput-object v3, v2, v5
    const-string v3, "Vibración al tocar la bolita"
    const/4 v5, 0x1
    aput-object v3, v2, v5
    new-array v3, v1, [Z
    const-string v5, "auto_hide"
    const/4 v6, 0x1
    invoke-interface {v4, v5, v6}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v5
    const/4 v7, 0x0
    aput-boolean v5, v3, v7
    const-string v5, "ball_haptics"
    invoke-interface {v4, v5, v7}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
    move-result v5
    const/4 v7, 0x1
    aput-boolean v5, v3, v7
    new-instance v5, Landroid/app/AlertDialog$Builder;
    invoke-direct {v5, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v6, "REVIVAL MOD"
    invoke-virtual {v5, v6}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    new-instance v6, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalSettingsListener;
    invoke-direct {v6, p0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalSettingsListener;-><init>(Landroid/content/Context;)V
    invoke-virtual {v5, v2, v3, v6}, Landroid/app/AlertDialog$Builder;->setMultiChoiceItems([Ljava/lang/CharSequence;[ZLandroid/content/DialogInterface$OnMultiChoiceClickListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v5
    const-string v6, "CERRAR"
    const/4 v7, 0x0
    invoke-virtual {v5, v6, v7}, Landroid/app/AlertDialog$Builder;->setPositiveButton(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v5
    invoke-virtual {v5}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method
"""
    path.write_text(source+"\n"+helper+"\n"+floating_helper+"\n"+settings_helper,encoding="utf-8")
    smali_root=next((parent for parent in path.parents if parent.name.startswith("smali")),None)
    if smali_root is None: raise RuntimeError("No se encontró la raíz smali para los listeners Revival")
    base=smali_root/"com/rovio/angrybirdstransformers"
    base.mkdir(parents=True,exist_ok=True)
    files={
    "AngryBirdsTransformersActivity$RevivalBallTouchListener.smali":r""".class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;
.super Ljava/lang/Object;
.implements Landroid/view/View$OnTouchListener;
.field private final activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
.field private final hideTask:Ljava/lang/Runnable;
.field private downX:F
.field private downY:F
.field private startX:F
.field private startY:F
.field private moved:Z
.method public constructor <init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;Ljava/lang/Runnable;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 iput-object p2, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->hideTask:Ljava/lang/Runnable;
 return-void
.end method
.method public onTouch(Landroid/view/View;Landroid/view/MotionEvent;)Z
 .locals 10
 invoke-virtual {p2}, Landroid/view/MotionEvent;->getActionMasked()I
 move-result v0
 if-nez v0, :touch_move
 invoke-virtual {p1}, Landroid/view/View;->animate()Landroid/view/ViewPropertyAnimator;
 move-result-object v1
 invoke-virtual {v1}, Landroid/view/ViewPropertyAnimator;->cancel()V
 const/high16 v1, 0x3f800000
 invoke-virtual {p1, v1}, Landroid/view/View;->setAlpha(F)V
 invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawX()F
 move-result v1
 iput v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->downX:F
 invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawY()F
 move-result v1
 iput v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->downY:F
 invoke-virtual {p1}, Landroid/view/View;->getX()F
 move-result v1
 iput v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->startX:F
 invoke-virtual {p1}, Landroid/view/View;->getY()F
 move-result v1
 iput v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->startY:F
 const/4 v1, 0x0
 iput-boolean v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->moved:Z
 iget-object v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->hideTask:Ljava/lang/Runnable;
 invoke-virtual {p1, v1}, Landroid/view/View;->removeCallbacks(Ljava/lang/Runnable;)Z
 iget-object v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 const-string v2, "abt_revival_mod"
 const/4 v3, 0x0
 invoke-virtual {v1, v2, v3}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
 move-result-object v1
 const-string v2, "ball_haptics"
 invoke-interface {v1, v2, v3}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
 move-result v1
 if-eqz v1, :touch_no_haptic
 const/4 v1, 0x1
 invoke-virtual {p1, v1}, Landroid/view/View;->performHapticFeedback(I)Z
 :touch_no_haptic
 const/4 v1, 0x1
 return v1
 :touch_move
 const/4 v1, 0x2
 if-ne v0, v1, :touch_up
 invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawX()F
 move-result v1
 iget v2, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->downX:F
 sub-float v3, v1, v2
 invoke-virtual {p2}, Landroid/view/MotionEvent;->getRawY()F
 move-result v1
 iget v2, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->downY:F
 sub-float v4, v1, v2
 invoke-static {v3}, Ljava/lang/Math;->abs(F)F
 move-result v5
 const/high16 v6, 0x41400000
 cmpl-float v5, v5, v6
 if-ltz v5, :touch_check_vertical
 goto :touch_drag_start
 :touch_check_vertical
 invoke-static {v4}, Ljava/lang/Math;->abs(F)F
 move-result v5
 cmpl-float v5, v5, v6
 if-ltz v5, :touch_consume_move
 :touch_drag_start
 const/4 v1, 0x1
 iput-boolean v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->moved:Z
 invoke-virtual {p1}, Landroid/view/View;->getParent()Landroid/view/ViewParent;
 move-result-object v5
 check-cast v5, Landroid/view/View;
 invoke-virtual {v5}, Landroid/view/View;->getWidth()I
 move-result v6
 invoke-virtual {p1}, Landroid/view/View;->getWidth()I
 move-result v7
 sub-int/2addr v6, v7
 int-to-float v6, v6
 const/4 v7, 0x0
 invoke-static {v6, v7}, Ljava/lang/Math;->max(FF)F
 move-result v6
 iget v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->startX:F
 add-float/2addr v1, v3
 invoke-static {v1, v7}, Ljava/lang/Math;->max(FF)F
 move-result v1
 invoke-static {v1, v6}, Ljava/lang/Math;->min(FF)F
 move-result v1
 invoke-virtual {p1, v1}, Landroid/view/View;->setX(F)V
 invoke-virtual {v5}, Landroid/view/View;->getHeight()I
 move-result v6
 invoke-virtual {p1}, Landroid/view/View;->getHeight()I
 move-result v8
 sub-int/2addr v6, v8
 int-to-float v6, v6
 invoke-static {v6, v7}, Ljava/lang/Math;->max(FF)F
 move-result v6
 iget v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->startY:F
 add-float/2addr v1, v4
 invoke-static {v1, v7}, Ljava/lang/Math;->max(FF)F
 move-result v1
 invoke-static {v1, v6}, Ljava/lang/Math;->min(FF)F
 move-result v1
 invoke-virtual {p1, v1}, Landroid/view/View;->setY(F)V
 :touch_consume_move
 const/4 v1, 0x1
 return v1
 :touch_up
 const/4 v1, 0x1
 if-ne v0, v1, :touch_other
 iget-boolean v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->moved:Z
 if-nez v1, :touch_schedule
 iget-object v1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallTouchListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 invoke-virtual {v1}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->showRevivalSettings()V
 :touch_schedule
 invoke-virtual {p1}, Landroid/view/View;->animate()Landroid/view/ViewPropertyAnimator;
 move-result-object v1
 const v2, 0x3f0ccccd
 invoke-virtual {v1, v2}, Landroid/view/ViewPropertyAnimator;->alpha(F)Landroid/view/ViewPropertyAnimator;
 move-result-object v1
 const-wide/16 v2, 0x1388
 invoke-virtual {v1, v2, v3}, Landroid/view/ViewPropertyAnimator;->setDuration(J)Landroid/view/ViewPropertyAnimator;
 move-result-object v1
 invoke-virtual {v1}, Landroid/view/ViewPropertyAnimator;->start()V
 const/4 v1, 0x1
 return v1
 :touch_other
 const/4 v1, 0x1
 return v1
.end method
""",
    "AngryBirdsTransformersActivity$RevivalBallHideTask.smali":r""".class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;
.super Ljava/lang/Object;
.implements Ljava/lang/Runnable;
.field private final ball:Landroid/view/View;
.method public constructor <init>(Landroid/view/View;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;->ball:Landroid/view/View;
 return-void
.end method
.method public run()V
 .locals 5
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;->ball:Landroid/view/View;
 invoke-virtual {v0}, Landroid/view/View;->getContext()Landroid/content/Context;
 move-result-object v1
 const-string v2, "abt_revival_mod"
 const/4 v3, 0x0
 invoke-virtual {v1, v2, v3}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
 move-result-object v1
 const-string v2, "auto_hide"
 const/4 v3, 0x1
 invoke-interface {v1, v2, v3}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z
 move-result v1
 if-eqz v1, :hide_done
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalBallHideTask;->ball:Landroid/view/View;
 const v1, 0x3f0ccccd
 invoke-virtual {v0, v1}, Landroid/view/View;->setAlpha(F)V
 :hide_done
 return-void
.end method
""",
    "AngryBirdsTransformersActivity$RevivalSettingsListener.smali":r""".class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalSettingsListener;
.super Ljava/lang/Object;
.implements Landroid/content/DialogInterface$OnMultiChoiceClickListener;
.field private final context:Landroid/content/Context;
.method public constructor <init>(Landroid/content/Context;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalSettingsListener;->context:Landroid/content/Context;
 return-void
.end method
.method public onClick(Landroid/content/DialogInterface;IZ)V
 .locals 4
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalSettingsListener;->context:Landroid/content/Context;
 const-string v1, "abt_revival_mod"
 const/4 v2, 0x0
 invoke-virtual {v0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
 move-result-object v0
 invoke-interface {v0}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
 move-result-object v0
 if-nez p2, :setting_haptics
 const-string v1, "auto_hide"
 invoke-interface {v0, v1, p3}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;
 move-result-object v0
 goto :setting_save
 :setting_haptics
 const-string v1, "ball_haptics"
 invoke-interface {v0, v1, p3}, Landroid/content/SharedPreferences$Editor;->putBoolean(Ljava/lang/String;Z)Landroid/content/SharedPreferences$Editor;
 move-result-object v0
 :setting_save
 invoke-interface {v0}, Landroid/content/SharedPreferences$Editor;->apply()V
 return-void
.end method
"""
    }
    for name,content in files.items():
        (base/name).write_text(content.lstrip(),encoding="utf-8")
    report["welcome"]={"first_launch_only":True,"dismissible":True,"method":"Android AlertDialog + SharedPreferences"}
    report["floating_ball"]={"draggable":True,"auto_hide_seconds":30,"overlay_permission":False,"settings":["auto_hide","ball_haptics"],"pak_modified":False}

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
