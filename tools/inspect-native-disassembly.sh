#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && -f "$1" ]] || { echo "Uso: $0 archivo.apk" >&2; exit 2; }
APK=$1
mkdir -p reports native-work
REPORT=reports/native-disassembly.txt
: > "$REPORT"
for cmd in unzip llvm-objdump llvm-nm llvm-readelf; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Falta herramienta: $cmd" >&2; exit 1; }
done
{
 echo "ABT Revival Mod — análisis de símbolos y desensamblado"
 echo "APK SHA-256: $(sha256sum "$APK" | awk '{print $1}')"
 echo
 for ABI in arm64-v8a armeabi-v7a; do
   LIB="lib/$ABI/libABBS.so"
   if ! unzip -Z1 "$APK" | grep -Fxq "$LIB"; then
     echo "No existe $LIB"; continue
   fi
   OUT="native-work/libABBS-$ABI.so"
   unzip -p "$APK" "$LIB" > "$OUT"
   echo "===== $ABI ====="
   echo "--- ELF ---"
   llvm-readelf -h "$OUT" | grep -E 'Class:|Machine:|Type:'
   echo
   echo "--- FPS symbols ---"
   llvm-nm -D -C "$OUT" 2>/dev/null | grep -Ei 'FrameRateLimiter|DesiredFramerate|LimitFPSWithSleep|Target30FPS|Target60FPS|XGSClampToTargetFPS|LowBatteryFPSCap' | head -n 160 || true
   echo
   echo "--- Disassembly of relevant exported functions ---"
   for SYM in '_ZN19CXGSRenderDeviceOGL19SetFrameRateLimiterEN12EXGSFPSLimit4EnumE' '_ZN19CXGSRenderDeviceOGL19GetFrameRateLimiterEv' '_ZN13CDeviceConfig19GetDesiredFramerateEv' '_ZN4CApp19GetDesiredFramerateEv' '_Z17LimitFPSWithSleepi'; do
     echo "### $SYM"
     llvm-objdump -d --demangle --disassemble-symbols="$SYM" "$OUT" 2>/dev/null | head -n 180 || true
   done
   echo
 done
 echo "NOTA: el desensamblado revela instrucciones y símbolos, pero la interpretación del flujo de ejecución requiere seguir referencias y validar en dispositivo."
} | tee "$REPORT"
