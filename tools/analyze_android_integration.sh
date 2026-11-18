#!/usr/bin/env bash
# XGS extraction validation is part of this diagnostic workflow.
# Exient XGS PAK research: inspect real APK headers before selecting XPK1/XPK2 extraction.
# Public format reference: https://github.com/WerWolv/ImHex-Patterns/blob/master/patterns/xgspak.hexpat
set -euo pipefail
[[ $# -eq 2 && -f "$1" ]] || { echo "Uso: $0 APK REPORT_DIR" >&2; exit 2; }
APK="$1"
OUT="$2"
mkdir -p "$OUT" "$RUNNER_TEMP/abt-decode"
DECODE="$RUNNER_TEMP/abt-decode"
REPORT="$OUT/android-integration-report.txt"
{
  echo "ABT Revival Mod — Android integration point analysis"
  echo "APK: $(basename "$APK")"
  echo "SHA-256: $(sha256sum "$APK" | awk '{print $1}')"
  echo
  echo "=== Package and launch activity (aapt) ==="
  aapt dump badging "$APK" | grep -E "^(package:|launchable-activity:|sdkVersion:|targetSdkVersion:|native-code:)" || true
  echo
  echo "=== Decode AndroidManifest.xml (private workspace) ==="
  apktool d -f "$APK" -o "$DECODE" >/dev/null
  if [[ -f "$DECODE/AndroidManifest.xml" ]]; then
    cp "$DECODE/AndroidManifest.xml" "$OUT/AndroidManifest-decoded.xml"
    grep -Eo 'android:name="[^"]+"|android:exported="[^"]+"|android:configChanges="[^"]+"' "$DECODE/AndroidManifest.xml" | sort -u | head -n 240 || true
  fi
  echo
  echo "=== DEX inventory ==="
  unzip -Z1 "$APK" | grep -E '^classes([0-9]+)?\.dex$' | sort -V || true
  echo
  echo "=== Native libraries ==="
  unzip -Z1 "$APK" | grep -E '^lib/[^/]+/[^/]+\.so$' | sort || true
  echo
  echo "=== Game asset path hints (names only) ==="
  find "$DECODE/assets" "$DECODE/res" -type f 2>/dev/null |
    grep -iE '(menu|ui|interface|button|settings|font|screen)' |
    sed "s#^$DECODE/##" | head -n 240 || true
  echo
  echo "=== Packed UI resource inventory and signatures (no payloads uploaded) ==="
  find "$DECODE/assets" -type f \( -iname '*.pak' -o -iname '*.manifest' \) -print 2>/dev/null | sort |
    while IFS= read -r asset; do
      echo "-- ${asset#"$DECODE/"} --"
      stat -c 'size_bytes=%s' "$asset" || true
      file "$asset" || true
      od -An -tx1 -N48 "$asset" 2>/dev/null || true
      if [[ "${asset,,}" == *.pak ]]; then
        python3 - "$asset" <<'PYPAK'
import os, struct, sys
path = sys.argv[1]
with open(path, "rb") as f:
    h = f.read(20)
if len(h) >= 20 and h[0] <= 2 and h[1:4] == b"KPX":
    version = h[0]
    folders, files, table_size = struct.unpack_from("<III", h, 4)
    compression = struct.unpack_from("<I", h, 16)[0] if version == 2 else None
    labels = {0: "raw", 1: "zlib", 2: "LZ4"}
    print(f"xgs_header=version{version} magic=KPX folders={folders} files={files} content_table_bytes={table_size}")
    if compression is not None:
        print(f"xgs_compression={compression} ({labels.get(compression, 'unknown')})")
else:
    print("xgs_header=unclassified (do not assume XPK variant)")
PYPAK
      fi
      if [[ "${asset,,}" == *.manifest ]]; then
        head -c 12000 "$asset" 2>/dev/null || true
        echo
      else
        strings -a "$asset" 2>/dev/null |
          grep -iE 'CSettingsScreen|ShowSettingsScreen|CWindow_PlayButton|MainSplash|EScreen_FE_|\.xml|\.atlas|\.png|\.dds|settings|button|menu' |
          head -n 100 || true
      fi
    done
  echo
  echo "=== Native UI identifier offsets (file offsets, text only) ==="
  for lib in "$DECODE/lib/arm64-v8a/libABBS.so" "$DECODE/lib/armeabi-v7a/libABBS.so"; do
    if [[ -f "$lib" ]]; then
      echo "-- ${lib#"$DECODE/"} --"
      strings -a -t x "$lib" |
        grep -iE 'CSettingsScreen|ShowSettingsScreen|CWindow_PlayButton|CWindow_MainSplashScreen|DeveloperMenuScreen|EScreen_FE_|UIPAK:|XMLPAK:' |
        head -n 180 || true
      if command -v readelf >/dev/null 2>&1; then
        readelf -Ws "$lib" 2>/dev/null |
          grep -iE 'settings|frontend|screen|window|menu|button|pak|resource' |
          head -n 100 || true
      fi
    fi
  done
  echo
  echo "=== Native game UI string hints (text only; no binaries uploaded) ==="
  for lib in "$DECODE/lib/arm64-v8a/libABBS.so" "$DECODE/lib/armeabi-v7a/libABBS.so"; do
    if [[ -f "$lib" ]] && command -v strings >/dev/null 2>&1; then
      echo "-- $(basename "$(dirname "$lib")")/$(basename "$lib") --"
      strings -a "$lib" |
        grep -iE 'menu|settings|button|screen|scene|interface|graphics|framerate|fps' |
        head -n 180 || true
    fi
  done
  echo
  echo "=== Smali activity / engine integration candidates ==="
  find "$DECODE" -type f -name '*.smali' -print0 |
    xargs -0 grep -lE 'UnityPlayerActivity|GameActivity|NativeActivity|SurfaceView|GLSurfaceView|onCreate\(|onResume\(|Choreographer|setFrameRate' 2>/dev/null |
    sed "s#^$DECODE/##" | head -n 240 || true
  echo
  echo "=== Lifecycle and rendering API references ==="
  find "$DECODE" -type f -name '*.smali' -print0 |
    xargs -0 grep -nE 'Landroid/view/Surface;->setFrameRate|Landroid/view/Window;->setPreferredRefreshRate|Landroid/view/Choreographer;|Landroid/view/SurfaceView;|Landroid/opengl/GLSurfaceView;' 2>/dev/null |
    head -n 240 || true
  echo
  echo "=== Selected integration smali (reviewable source excerpts) ==="
  mkdir -p "$OUT/integration-smali"
  for rel in \
    "smali_classes5/com/rovio/angrybirdstransformers/AngryBirdsTransformersActivity.smali" \
    "smali/com/exient/ExientGLSurfaceView.smali" \
    "smali/com/exient/XGS/XGSActivity.smali"; do
    if [[ -f "$DECODE/$rel" ]]; then
      mkdir -p "$OUT/integration-smali/$(dirname "$rel")"
      cp "$DECODE/$rel" "$OUT/integration-smali/$rel"
      echo "Included: $rel"
    else
      echo "Not found: $rel"
    fi
  done
  for name in ExientActivity.smali 'ExientGLSurfaceView$Renderer.smali'; do
    while IFS= read -r found; do
      rel="$(printf '%s' "$found" | sed "s#^$DECODE/##")"
      mkdir -p "$OUT/integration-smali/$(dirname "$rel")"
      cp "$found" "$OUT/integration-smali/$rel"
      echo "Included: $rel"
    done < <(find "$DECODE" -type f -name "$name" -print)
  done
  echo
  echo "=== Engine activity and GL renderer integration references ==="
  find "$DECODE" -type f \( -name 'ExientActivity.smali' -o -name 'ExientGLSurfaceView$Renderer.smali' \) -print0 |
    xargs -0 grep -nE '^\.method|onCreate|onResume|onPause|setContentView|addContentView|addView|ExientGLSurfaceView|setRenderer|onDrawFrame|eglSwapBuffers|setFrameRate|LimitFPS|GetDesiredFramerate' 2>/dev/null |
    head -n 300 || true
  echo
  echo "=== Main activity lifecycle, view creation and layout references ==="
  ACTIVITY="$DECODE/smali_classes5/com/rovio/angrybirdstransformers/AngryBirdsTransformersActivity.smali"
  if [[ -f "$ACTIVITY" ]]; then
    grep -nE '^\.method|onCreate|onResume|onPause|setContentView|addContentView|addView|Exient|XGSActivity|GLSurfaceView' "$ACTIVITY" | head -n 220 || true
  fi
  echo
  echo "=== Safety note ==="
  echo "Selected activity, GL view, XGS activity and renderer smali source files are included in the private diagnostics artifact for integration review; all other decoded resources stay in the runner workspace."
  echo "The private artifact contains text diagnostics, the decoded manifest and selected integration smali files; no APK, textures, audio or other game assets are uploaded."
} > "$REPORT"

echo >> "$REPORT"
echo "=== XGS v2/zlib UI PAK extraction and text inventory ===" >> "$REPORT"
python3 tools/extract_xgs_pak.py "$APK" --all-paks --out "$RUNNER_TEMP/xgs-ui-extracted" --report "$OUT/xgs-pak-inventory.txt" >> "$REPORT"
cat "$OUT/xgs-pak-inventory.txt" >> "$REPORT"

 
echo >> "$REPORT"
echo "=== Verified XOX2 settings screen decode (structure only) ===" >> "$REPORT"
SETTINGS_XML="$(find "$RUNNER_TEMP/xgs-ui-extracted" -type f -iname 'uisettingsscreen.xml' -print -quit)"
if [[ -n "$SETTINGS_XML" && -x "${ABGTOOL:-}" ]]; then
  python3 - "$ABGTOOL" "$SETTINGS_XML" "$OUT/xox2-settings-structure.txt" <<'PYXOX'
import subprocess, sys, xml.etree.ElementTree as ET
tool, source, output = sys.argv[1:]
run = subprocess.run([tool, "xox", source], check=True, text=True, capture_output=True)
root = ET.fromstring(run.stdout)
lines = ["Decoded XOX2 settings hierarchy (selected structural fields only)."]
def walk(node, depth=0):
    tag = node.tag.rsplit("}", 1)[-1]
    attrs = []
    for key, value in node.attrib.items():
        k = key.rsplit("}", 1)[-1]
        if any(term in (k + " " + value).lower() for term in
               ("settings", "page", "button", "globalstate", "action", "label", "rategame", "mute", "restore", "zendesk", "login", "privacy", "erase", "powersave", "jenga", "featureconfig")):
            attrs.append(f'{k}={value!r}')
    if any(term in tag.lower() for term in ("settings", "page", "button", "window", "behaviour", "panel", "screen", "touch")) or attrs:
        lines.append("  " * min(depth, 12) + tag + ((" " + " ".join(attrs)) if attrs else ""))
    for child in list(node):
        walk(child, depth + 1)
walk(root)
open(output, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"Decoded XOX2 settings XML successfully: {len(list(root.iter()))} XML nodes")
PYXOX
  cat "$OUT/xox2-settings-structure.txt" >> "$REPORT"
else
  echo "Settings XML or verified decoder unavailable; no asset was modified." >> "$REPORT"
  exit 1
fi
