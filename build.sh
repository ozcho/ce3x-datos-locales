#!/usr/bin/env bash
# Ejecuta las pruebas y compila el instalador con Inno Setup.
#
# En Linux hace falta Wine y una instalacion de Inno Setup en un prefijo propio:
#   curl -fLO https://github.com/jrsoftware/issrc/releases/download/is-6_2_2/innosetup-6.2.2.exe
#   WINEPREFIX=~/.wine-inno wine innosetup-6.2.2.exe /VERYSILENT /SUPPRESSMSGBOXES
set -euo pipefail

cd "$(dirname "$0")"

ISS=installer/ComplementoDatosLocales.iss
ISCC_WIN='C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
: "${WINEPREFIX:=$HOME/.wine-inno}"
export WINEPREFIX WINEDEBUG=-all

echo ">> pruebas"
python3 tests/test_plugin.py

echo ">> instalador"
mkdir -p dist
if command -v ISCC.exe > /dev/null 2>&1; then
    ISCC.exe "$ISS"
elif command -v wine > /dev/null 2>&1; then
    wine "$ISCC_WIN" "$ISS" 2>&1 | grep -viE 'libEGL|pci id|^\s*$'
else
    echo "No se encuentra ISCC.exe ni wine." >&2
    exit 1
fi

ls -la dist/
