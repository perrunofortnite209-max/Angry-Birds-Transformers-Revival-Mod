#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.tools"
mkdir -p "$TOOLS"
if [[ -x "$TOOLS/ghidra/support/analyzeHeadless" ]]; then
  echo "$TOOLS/ghidra"
  exit 0
fi
sudo apt-get update
sudo apt-get install -y openjdk-21-jdk unzip curl jq
API="$(curl -fsSL https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest)"
URL="$(jq -r '.assets[] | select(.name | test("^ghidra_.*PUBLIC_.*zip$")) | .browser_download_url' <<< "$API" | head -n1)"
[[ -n "$URL" && "$URL" != "null" ]] || { echo "No se encontró el ZIP público de Ghidra" >&2; exit 1; }
curl -fL --retry 3 "$URL" -o "$TOOLS/ghidra.zip"
mkdir -p "$TOOLS/unpack"
unzip -q "$TOOLS/ghidra.zip" -d "$TOOLS/unpack"
DIR="$(find "$TOOLS/unpack" -mindepth 1 -maxdepth 1 -type d -name 'ghidra_*' | head -n1)"
[[ -n "$DIR" ]] || { echo "No se pudo localizar Ghidra extraído" >&2; exit 1; }
mv "$DIR" "$TOOLS/ghidra"
rm -rf "$TOOLS/unpack" "$TOOLS/ghidra.zip"
"$TOOLS/ghidra/support/analyzeHeadless" -version || true
echo "$TOOLS/ghidra"
