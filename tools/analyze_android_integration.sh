#!/usr/bin/env bash
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
  find "$DECODE/assets" -type f \\( -iname '*.pak' -o -iname '*.manifest' \\) -print 2>/dev/null | sort |
    while IFS= read -r asset; do
      echo "-- ${asset#"$DECODE/"} --"
      stat -c 'size_bytes=%s' "$asset" || true
      file "$asset" || true
      od -An -tx1 -N48 "$asset" 2>/dev/null || true
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
