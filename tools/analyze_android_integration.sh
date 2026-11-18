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
  echo "=== Safety note ==="
  echo "Decoded proprietary resources and smali stay in the private runner workspace and are not uploaded."
  echo "Only text diagnostics and the decoded manifest are uploaded; no APK or game assets are published."
} > "$REPORT"
