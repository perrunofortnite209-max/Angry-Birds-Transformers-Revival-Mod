#!/usr/bin/env python3
"""Replace the placeholder MOD dialog with real JNI-backed FPS and graphics controls."""
from __future__ import annotations
import re
from pathlib import Path

DESC = "Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;"

def find_activity(decoded: Path) -> Path:
    hits=[]
    for p in decoded.glob("smali*/**/*.smali"):
        try: s=p.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        if re.search(r"^\.class\b.*"+re.escape(DESC),s,re.M): hits.append(p)
    if len(hits)!=1: raise RuntimeError(f"Activity not unique: {len(hits)}")
    return hits[0]

def method(name, body):
    pattern=re.compile(r"(?ms)^\.method[^\n]*\b"+re.escape(name)+r"\b.*?^\.end method")
    return pattern, body.strip()+"\n"

def patch(decoded: Path, report: dict):
    path=find_activity(decoded); source=path.read_text(encoding="utf-8")
    # Preserve the existing auto-hide / haptics checkboxes under a separate submenu.
    old_pattern=re.compile(r"(?ms)^\.method public showRevivalSettings\(\)V.*?^\.end method")
    old=old_pattern.search(source)
    if not old: raise RuntimeError("Existing floating-ball settings method not found")
    old_method=old.group(0).replace("showRevivalSettings()V","showRevivalBallOptions()V",1)
    source=source[:old.start()]+old_method+source[old.end():]
    # Main menu.
    main=r"""
.method public showRevivalSettings()V
    .locals 5
    new-instance v0, Landroid/app/AlertDialog$Builder;
    invoke-direct {v0, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v1, "REVIVAL MOD"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const/4 v1, 0x4
    new-array v1, v1, [Ljava/lang/CharSequence;
    const-string v2, "Límite de FPS"
    const/4 v3, 0x0
    aput-object v2, v1, v3
    const-string v2, "Calidad gráfica"
    const/4 v3, 0x1
    aput-object v2, v1, v3
    const-string v2, "Opciones de la bolita"
    const/4 v3, 0x2
    aput-object v2, v1, v3
    const-string v2, "Optimización CPU (60 FPS + gráficos bajos)"
    const/4 v3, 0x3
    aput-object v2, v1, v3
    new-instance v2, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalMenuClickListener;
    invoke-direct {v2, p0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalMenuClickListener;-><init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
    invoke-virtual {v0, v1, v2}, Landroid/app/AlertDialog$Builder;->setItems([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method
"""
    fps_dialog=r"""
.method public showRevivalFpsDialog()V
    .locals 5
    new-instance v0, Landroid/app/AlertDialog$Builder;
    invoke-direct {v0, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v1, "LÍMITE DE FPS"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const/4 v1, 0x6
    new-array v1, v1, [Ljava/lang/CharSequence;
    const-string v2, "30 FPS"
    const/4 v3, 0x0
    aput-object v2, v1, v3
    const-string v2, "60 FPS"
    const/4 v3, 0x1
    aput-object v2, v1, v3
    const-string v2, "90 FPS"
    const/4 v3, 0x2
    aput-object v2, v1, v3
    const-string v2, "120 FPS"
    const/4 v3, 0x3
    aput-object v2, v1, v3
    const-string v2, "140 FPS"
    const/4 v3, 0x4
    aput-object v2, v1, v3
    const-string v2, "Sin límite"
    const/4 v3, 0x5
    aput-object v2, v1, v3
    new-instance v2, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalFpsListener;
    invoke-direct {v2, p0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalFpsListener;-><init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
    invoke-virtual {v0, v1, v2}, Landroid/app/AlertDialog$Builder;->setItems([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method
"""
    graphics_dialog=r"""
.method public showRevivalGraphicsDialog()V
    .locals 5
    new-instance v0, Landroid/app/AlertDialog$Builder;
    invoke-direct {v0, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V
    const-string v1, "CALIDAD GRÁFICA"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    const/4 v1, 0x4
    new-array v1, v1, [Ljava/lang/CharSequence;
    const-string v2, "Baja  ·  android-generic_low"
    const/4 v3, 0x0
    aput-object v2, v1, v3
    const-string v2, "Media  ·  android-generic_medium"
    const/4 v3, 0x1
    aput-object v2, v1, v3
    const-string v2, "Alta  ·  android-generic_high"
    const/4 v3, 0x2
    aput-object v2, v1, v3
    const-string v2, "Experimental  ·  android-generic_extrahigh"
    const/4 v3, 0x3
    aput-object v2, v1, v3
    new-instance v2, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalGraphicsListener;
    invoke-direct {v2, p0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalGraphicsListener;-><init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
    invoke-virtual {v0, v1, v2}, Landroid/app/AlertDialog$Builder;->setItems([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method
"""

    apply_fps=r"""
.method public applyRevivalFps(I)V
    .locals 5
    packed-switch p1, :fps_switch_data
    const/4 v0, -0x1
    goto :fps_call
    :fps_30
    const/16 v0, 0x1e
    goto :fps_call
    :fps_60
    const/16 v0, 0x3c
    goto :fps_call
    :fps_90
    const/16 v0, 0x5a
    goto :fps_call
    :fps_120
    const/16 v0, 0x78
    goto :fps_call
    :fps_140
    const/16 v0, 0x8c
    goto :fps_call
    :fps_unlimited
    const/4 v0, 0x0
    :fps_call
    invoke-static {v0}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setFps(I)I
    move-result v1
    if-lez v1, :fps_failed
    const-string v2, "abt_revival_mod"
    const/4 v3, 0x0
    invoke-virtual {p0, v2, v3}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v2
    invoke-interface {v2}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v2
    const-string v3, "fps_limit"
    invoke-interface {v2, v3, v0}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;
    move-result-object v2
    invoke-interface {v2}, Landroid/content/SharedPreferences$Editor;->apply()V
    const-string v2, "Límite FPS aplicado"
    goto :fps_toast
    :fps_failed
    const-string v2, "No se pudo aplicar el límite FPS"
    :fps_toast
    const/4 v3, 0x0
    invoke-static {p0, v2, v3}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v4
    invoke-virtual {v4}, Landroid/widget/Toast;->show()V
    return-void
    :fps_switch_data
    .packed-switch 0x0
        :fps_30
        :fps_60
        :fps_90
        :fps_120
        :fps_140
        :fps_unlimited
    .end packed-switch
.end method
"""
    apply_graphics=r"""
.method public applyRevivalGraphics(I)V
    .locals 7
    # Read the live engine profile first. Negative values identify a missing
    # engine library or a bad native getter before attempting any mutation.
    invoke-static {}, Lcom/rovio/angrybirdstransformers/RevivalNative;->getGraphicsLevel()I
    move-result v1
    if-gez v1, :graphics_engine_ready
    move v0, v1
    goto :graphics_diagnostic_failed
    :graphics_engine_ready
    invoke-static {p1}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setGraphicsLevel(I)I
    move-result v0
    if-lez v0, :graphics_read_after_failure
    const-string v1, "abt_revival_mod"
    const/4 v2, 0x0
    invoke-virtual {p0, v1, v2}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v1
    invoke-interface {v1}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v1
    const-string v2, "graphics_profile"
    invoke-interface {v1, v2, p1}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;
    move-result-object v1
    invoke-interface {v1}, Landroid/content/SharedPreferences$Editor;->apply()V
    packed-switch p1, :graphics_switch_data
    const-string v3, "Perfil gráfico aplicado."
    goto :graphics_toast
    :graphics_low
    const-string v3, "Calidad baja aplicada."
    goto :graphics_toast
    :graphics_medium
    const-string v3, "Calidad media aplicada."
    goto :graphics_toast
    :graphics_high
    const-string v3, "Calidad alta aplicada."
    goto :graphics_toast
    :graphics_extra
    const-string v3, "Calidad experimental aplicada."
    goto :graphics_toast
    :graphics_read_after_failure
    invoke-static {}, Lcom/rovio/angrybirdstransformers/RevivalNative;->getGraphicsLevel()I
    move-result v1
    :graphics_diagnostic_failed
    new-instance v2, Ljava/lang/StringBuilder;
    const-string v3, "Error gráfico "
    invoke-direct {v2, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V
    invoke-static {v0}, Ljava/lang/Integer;->toString(I)Ljava/lang/String;
    move-result-object v3
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v3, " | nivel actual "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-static {v1}, Ljava/lang/Integer;->toString(I)Ljava/lang/String;
    move-result-object v3
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v3
    :graphics_toast
    const/4 v2, 0x0
    invoke-static {p0, v3, v2}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v4
    invoke-virtual {v4}, Landroid/widget/Toast;->show()V
    return-void
    :graphics_switch_data
    .packed-switch 0x0
        :graphics_low
        :graphics_medium
        :graphics_high
        :graphics_extra
    .end packed-switch
.end method
"""
    # Remove previous helpers if this patch is rerun, then append new versions.
    for name in ("showRevivalSettings()V","showRevivalFpsDialog()V","showRevivalGraphicsDialog()V","applyRevivalFps(I)V","applyRevivalGraphics(I)V","applySavedRevivalSettings()V"):
        pat=re.compile(r"(?ms)^\.method[^\n]*\b"+re.escape(name)+r".*?^\.end method\n?")
        source=pat.sub("",source)
    source += "\n"+main+"\n"+fps_dialog+"\n"+graphics_dialog+"\n"+apply_fps+"\n"+apply_graphics
    restore_helper=r"""
.method public applySavedRevivalSettings()V
    .locals 5
    const-string v0, "abt_revival_mod"
    const/4 v1, 0x0
    invoke-virtual {p0, v0, v1}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v0

    const-string v1, "graphics_profile"
    const/4 v2, -0x1
    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I
    move-result v2
    if-ltz v2, :restore_fps
    const/4 v3, 0x3
    if-gt v2, v3, :restore_fps
    invoke-static {v2}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setGraphicsLevel(I)I

    :restore_fps
    const-string v1, "fps_limit"
    const/4 v2, -0x1
    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getInt(Ljava/lang/String;I)I
    move-result v2
    const/4 v3, -0x1
    if-eq v2, v3, :restore_done
    invoke-static {v2}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setFps(I)I
    :restore_done
    return-void
.end method
"""
    source += "\n"+restore_helper+"\n"

    # Reapply saved settings once Android has resumed the game Activity.
    resume_pattern=re.compile(r"(?ms)^\.method[^\n]*\bonResume\(\)V\b.*?^\.end method")
    resume_match=resume_pattern.search(source)
    if resume_match:
        resume_method=resume_match.group(0)
        if "applySavedRevivalSettings()V" not in resume_method:
            super_call=re.search(r"(?m)^\s*invoke-super \{p0\}, .*->onResume\(\)V\s*$",resume_method)
            if super_call:
                pos=super_call.end()
                resume_method=resume_method[:pos]+"\n    invoke-virtual {p0}, "+DESC+"->applySavedRevivalSettings()V"+resume_method[pos:]
            else:
                returns=list(re.finditer(r"(?m)^\s*return-void\s*$",resume_method))
                if not returns: raise RuntimeError("onResume exists but has no return-void")
                pos=returns[-1].start()
                resume_method=resume_method[:pos]+"    invoke-virtual {p0}, "+DESC+"->applySavedRevivalSettings()V\n"+resume_method[pos:]
            source=source[:resume_match.start()]+resume_method+source[resume_match.end():]
    else:
        super_match=re.search(r"(?m)^\.super\s+(\S+)",source)
        super_desc=super_match.group(1) if super_match else "Landroid/app/Activity;"
        source += "\n.method protected onResume()V\n    .locals 0\n    invoke-super {p0}, "+super_desc+"->onResume()V\n    invoke-virtual {p0}, "+DESC+"->applySavedRevivalSettings()V\n    return-void\n.end method\n"


    cpu_helper=r"""
.method public applyRevivalCpuOptimization()V
    .locals 5
    # Balanced preset: lower render complexity and cap at 60 FPS to reduce frame workload.
    const/4 v0, 0x0
    invoke-static {v0}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setGraphicsLevel(I)I
    move-result v1
    const/16 v0, 0x3c
    invoke-static {v0}, Lcom/rovio/angrybirdstransformers/RevivalNative;->setFps(I)I
    move-result v2
    const-string v3, "abt_revival_mod"
    const/4 v4, 0x0
    invoke-virtual {p0, v3, v4}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;
    move-result-object v3
    invoke-interface {v3}, Landroid/content/SharedPreferences;->edit()Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    const-string v4, "graphics_profile"
    const/4 v0, 0x0
    invoke-interface {v3, v4, v0}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    const-string v4, "fps_limit"
    const/16 v0, 0x3c
    invoke-interface {v3, v4, v0}, Landroid/content/SharedPreferences$Editor;->putInt(Ljava/lang/String;I)Landroid/content/SharedPreferences$Editor;
    move-result-object v3
    invoke-interface {v3}, Landroid/content/SharedPreferences$Editor;->apply()V
    if-lez v1, :cpu_failed
    if-lez v2, :cpu_failed
    const-string v0, "Optimización aplicada: 60 FPS y gráficos bajos."
    goto :cpu_toast
    :cpu_failed
    const-string v0, "No se pudo aplicar todo el perfil."
    :cpu_toast
    const/4 v1, 0x0
    invoke-static {p0, v0, v1}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v2
    invoke-virtual {v2}, Landroid/widget/Toast;->show()V
    return-void
.end method
"""
    source += "\n"+cpu_helper+"\n"
    path.write_text(source,encoding="utf-8")

    smali_root=next((p for p in path.parents if p.name.startswith("smali")),None)
    if smali_root is None: raise RuntimeError("smali root not found")
    base=smali_root/"com/rovio/angrybirdstransformers"; base.mkdir(parents=True,exist_ok=True)
    (base/"RevivalNative.smali").write_text(r"""
.class public final Lcom/rovio/angrybirdstransformers/RevivalNative;
.super Ljava/lang/Object;
.method static constructor <clinit>()V
    .locals 1
    const-string v0, "abtmod"
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    return-void
.end method
.method public static native setFps(I)I
.end method
.method public static native getGraphicsLevel()I
.end method
.method public static native changeGraphics(I)I
.end method
.method public static native setGraphicsLevel(I)I
.end method
""".strip()+"\n",encoding="utf-8")
    (base/"AngryBirdsTransformersActivity$RevivalMenuClickListener.smali").write_text(r"""
.class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalMenuClickListener;
.super Ljava/lang/Object;
.implements Landroid/content/DialogInterface$OnClickListener;
.field private final activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
.method public constructor <init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalMenuClickListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 return-void
.end method
.method public onClick(Landroid/content/DialogInterface;I)V
 .locals 1
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalMenuClickListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 if-nez p2, :menu_graphics
 invoke-virtual {v0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->showRevivalFpsDialog()V
 return-void
 :menu_graphics
 const/4 v1, 0x1
 if-ne p2, v1, :menu_ball
 invoke-virtual {v0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->showRevivalGraphicsDialog()V
 return-void
 :menu_ball
 const/4 v1, 0x2
 if-ne p2, v1, :menu_cpu
 invoke-virtual {v0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->showRevivalBallOptions()V
 return-void
 :menu_cpu
 invoke-virtual {v0}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->applyRevivalCpuOptimization()V
 return-void
.end method
""".strip()+"\n",encoding="utf-8")
    (base/"AngryBirdsTransformersActivity$RevivalFpsListener.smali").write_text(r"""
.class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalFpsListener;
.super Ljava/lang/Object;
.implements Landroid/content/DialogInterface$OnClickListener;
.field private final activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
.method public constructor <init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalFpsListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 return-void
.end method
.method public onClick(Landroid/content/DialogInterface;I)V
 .locals 1
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalFpsListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 invoke-virtual {v0, p2}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->applyRevivalFps(I)V
 return-void
.end method
""".strip()+"\n",encoding="utf-8")
    (base/"AngryBirdsTransformersActivity$RevivalGraphicsListener.smali").write_text(r"""
.class public final Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalGraphicsListener;
.super Ljava/lang/Object;
.implements Landroid/content/DialogInterface$OnClickListener;
.field private final activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
.method public constructor <init>(Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;)V
 .locals 0
 invoke-direct {p0}, Ljava/lang/Object;-><init>()V
 iput-object p1, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalGraphicsListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 return-void
.end method
.method public onClick(Landroid/content/DialogInterface;I)V
 .locals 1
 iget-object v0, p0, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity$RevivalGraphicsListener;->activity:Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;
 invoke-virtual {v0, p2}, Lcom/rovio/angrybirdstransformers/AngryBirdsTransformersActivity;->applyRevivalGraphics(I)V
 return-void
.end method
""".strip()+"\n",encoding="utf-8")
    report["runtime_controls"]={"fps_options":[30,60,90,120,140,"unlimited"],"graphics_profiles":["android-generic_low","android-generic_medium","android-generic_high","android-generic_extrahigh"],"graphics_switch":"LoadDeviceConfigByPerformance + renderer refresh","jni_bridge":True,"runtime_abi":"arm64"}
