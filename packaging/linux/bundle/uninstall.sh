#!/bin/sh
# Entfernt kimbaview (aktueller Benutzer). Persönliche Einstellungen in
# ~/.config/kimbaview bleiben erhalten – bei Bedarf von Hand löschen.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA/kimbaview"
LINK="$HOME/.local/bin/kimbaview"

sh "$HERE/desktop/uninstall.sh"

# Nur unseren eigenen Link entfernen, nie eine fremde Datei gleichen Namens.
if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$PREFIX/venv/bin/kimbaview" ]; then
    rm -f "$LINK"
fi
case "$PREFIX" in
    */kimbaview) rm -rf "$PREFIX" ;;
esac
echo "kimbaview wurde entfernt. (Einstellungen: ${XDG_CONFIG_HOME:-$HOME/.config}/kimbaview)"
