#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Uso: $0 /ruta/al/archivo.apk" >&2
  exit 2
fi
for cmd in unzip strings sha256sum grep; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Falta la herramienta requerida: $cmd" >&2
    exit 1
  }
done

APK=$1
REPORT_DIR="reports"
REPORT="$REPORT_DIR/native-fps-analysis.txt"
mkdir -p "$REPORT_DIR"

{
  echo "Angry Birds Transformers — análisis nativo de solo lectura"
  echo "Fecha UTC: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  echo "Archivo: $(basename "$APK")"
  echo "Tamaño: $(stat -c '%s bytes' "$APK" 2>/dev/null || wc -c < "$APK")"
  echo "SHA-256: $(sha256sum "$APK" | awk '{print $1}')"
  echo
  echo "=== Validación ZIP ==="
  unzip -tq "$APK" >/dev/null
  echo "ZIP/APK íntegro: sí"
  echo
  echo "=== Bibliotecas ABBS encontradas ==="
  mapfile -t LIBS < <(unzip -Z1 "$APK" | grep -E '^lib/(arm64-v8a|armeabi-v7a)/libABBS\.so$' || true)
  if [[ ${#LIBS[@]} -eq 0 ]]; then
    echo "No se encontraron las bibliotecas ABBS esperadas."
  else
    for LIB in "${LIBS[@]}"; do
      echo
      echo "--- $LIB ---"
      unzip -p "$APK" "$LIB" | strings -a | grep -Ei 'TARGET_[0-9]+_FPS|Target[0-9]+FPS|LowBatteryFPSCap|Framerate|frame.?time|fps' | sort -u | head -n 250 || true
    done
  fi
  echo
  echo "=== Límites de este informe ==="
  echo "Las cadenas encontradas son indicios, no identifican por sí solas la función que aplica el límite."
  echo "Este script NO modifica el APK, no altera bibliotecas y no desbloquea FPS."
} > "$REPORT"

cat "$REPORT"
echo
echo "Informe guardado en: $REPORT"
