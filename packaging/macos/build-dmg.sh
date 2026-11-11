#!/bin/sh
# Baut dist/kimbaview.app und dist/kimbaview-<version>-macos-<arch>.dmg.
#
#   sh packaging/macos/build-dmg.sh            (im Projektordner, aktive venv mit "pip install . py2app")
#
# Signieren/Notarisieren passiert automatisch, wenn diese Umgebungsvariablen gesetzt sind
# (in GitHub Actions als Repository-Secrets):
#   MACOS_SIGN_IDENTITY   z. B. "Developer ID Application: Vorname Nachname (TEAMID)"
#   MACOS_NOTARY_KEY_PATH, MACOS_NOTARY_KEY_ID, MACOS_NOTARY_ISSUER   (App-Store-Connect-API-Schlüssel)
# Ohne diese Variablen wird die App nur "ad hoc" signiert (läuft, zeigt aber den Gatekeeper-Hinweis).
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
PY=${PYTHON:-python3}
VERSION=$("$PY" -c 'import sys; sys.path.insert(0, "src"); import kimbaview; print(kimbaview.__version__)')
ARCH=$(uname -m)
APP="dist/kimbaview.app"
DMG="dist/kimbaview-$VERSION-macos-$ARCH.dmg"

rm -rf "$APP" build/py2app
"$PY" packaging/macos/setup_py2app.py py2app

# Selbsttest des fertigen Bundles (ohne Fenster)
"$APP/Contents/MacOS/kimbaview" --selftest

if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
    echo "Signiere mit: $MACOS_SIGN_IDENTITY"
    codesign --force --deep --options runtime --timestamp \
        --entitlements packaging/macos/entitlements.plist \
        --sign "$MACOS_SIGN_IDENTITY" "$APP"
else
    echo "Keine Signatur-Identität gesetzt – ad-hoc-Signatur."
    codesign --force --deep --sign - "$APP"
fi
codesign --verify --deep --strict "$APP"

# DMG mit Verknüpfung auf "Programme" (zum Hineinziehen)
STAGE="build/dmg"
rm -rf "$STAGE" "$DMG"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Programme"
cp LICENSE "$STAGE/LICENSE.txt"
hdiutil create -volname "kimbaview $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG"

if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
    codesign --force --timestamp --sign "$MACOS_SIGN_IDENTITY" "$DMG"
    if [ -n "${MACOS_NOTARY_KEY_PATH:-}" ]; then
        echo "Notarisiere bei Apple (kann einige Minuten dauern) …"
        xcrun notarytool submit "$DMG" --wait \
            --key "$MACOS_NOTARY_KEY_PATH" --key-id "$MACOS_NOTARY_KEY_ID" --issuer "$MACOS_NOTARY_ISSUER"
        xcrun stapler staple "$DMG"
        spctl --assess --type open --context context:primary-signature -v "$DMG" || true
    fi
fi
echo "Fertig: $DMG"
