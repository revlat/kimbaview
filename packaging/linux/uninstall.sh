#!/bin/sh
# Entfernt die "Öffnen mit"-Registrierung von kimbaview für den aktuellen Benutzer.
set -eu

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS="$DATA/applications"
MIME="$DATA/mime"

rm -f "$APPS/kimbaview.desktop" "$MIME/packages/kimbaview-mediawiki.xml" \
      "$DATA/icons/hicolor/256x256/apps/kimbaview.png"

command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME" || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" || true

echo "kimbaview-Registrierung entfernt."
