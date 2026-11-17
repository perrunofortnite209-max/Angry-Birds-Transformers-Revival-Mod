#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Uso: $0 /ruta/al/archivo.apk" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
APK=$1

if [[ ! -f "$APK" ]]; then
  echo "Error: no existe el archivo: $APK" >&2
  exit 1
fi

echo "=== Archivo ==="
printf 'Ruta: %s\n' "$APK"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$APK"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$APK"
else
  echo "Aviso: instala sha256sum o shasum para calcular el hash."
fi

echo
echo "=== Manifiesto Android ==="
if command -v apkanalyzer >/dev/null 2>&1; then
  for field in application-id version-code version-name min-sdk target-sdk; do
    printf '%s: ' "$field"
    apkanalyzer manifest "$field" "$APK" 2>/dev/null || echo "no disponible"
  done
elif command -v aapt >/dev/null 2>&1; then
  aapt dump badging "$APK" 2>/dev/null | grep -E "^(package:|sdkVersion:|targetSdkVersion:)" || true
else
  echo "No se encontró apkanalyzer ni aapt; instala Android SDK Build Tools."
fi

echo
echo "=== Bibliotecas nativas (ABI) ==="
if command -v unzip >/dev/null 2>&1; then
  ABI_LIST=$(unzip -Z1 "$APK" | awk -F/ '$1 == "lib" && NF >= 3 && $3 ~ /\.so$/ { print $2 }' | sort -u)
  if [[ -n "$ABI_LIST" ]]; then
    printf '%s\n' "$ABI_LIST"
    echo
    echo "Bibliotecas:"
    unzip -Z1 "$APK" | awk '$1 ~ /^lib\/[^/]+\/.*\.so$/ { print }'
  else
    echo "No se encontraron bibliotecas .so empaquetadas."
  fi
else
  echo "No se encontró unzip; no se pudo listar el contenido del APK."
fi
