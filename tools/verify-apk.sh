#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "Uso: $0 /ruta/al/archivo.apk" >&2
  exit 2
fi

if ! command -v apksigner >/dev/null 2>&1; then
  echo "Error: no se encontró apksigner. Instala Android SDK Build Tools." >&2
  exit 1
fi

APK=$1
echo "Verificando firma: $APK"
apksigner verify --verbose --print-certs "$APK"
