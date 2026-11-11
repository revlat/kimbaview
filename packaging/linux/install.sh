#!/bin/sh
# Registriert kimbaview für den aktuellen Benutzer als "Öffnen mit"-Programm
# (Markdown: text/markdown, MediaWiki: eigener Typ text/x-mediawiki).
# Keine Root-Rechte nötig. Das Standardprogramm wird nicht geändert.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS="$DATA/applications"
MIME="$DATA/mime"

mkdir -p "$APPS" "$MIME/packages"

# Startmenü-Einträge kennen oft nicht den PATH der Shell (z. B. ~/.local/bin).
# Daher, falls auffindbar, den absoluten Pfad einsetzen.
BIN=${KIMBAVIEW_BIN:-$(command -v kimbaview 2>/dev/null || true)}
if [ -n "$BIN" ]; then
    case "$BIN" in
        *[!A-Za-z0-9/._-]*) echo "Pfad enthält Sonderzeichen, nutze 'kimbaview' aus PATH: $BIN" >&2; BIN=kimbaview ;;
    esac
else
    echo "Hinweis: 'kimbaview' ist nicht im PATH – der Eintrag nutzt 'Exec=kimbaview %f'." >&2
    BIN=kimbaview
fi

sed "s|^Exec=kimbaview %f|Exec=$BIN %f|" "$HERE/kimbaview.desktop" > "$APPS/kimbaview.desktop"
chmod 644 "$APPS/kimbaview.desktop"
install -m 644 "$HERE/kimbaview-mediawiki.xml" "$MIME/packages/kimbaview-mediawiki.xml"
ICONS="$DATA/icons/hicolor/256x256/apps"
mkdir -p "$ICONS"
install -m 644 "$HERE/kimbaview.png" "$ICONS/kimbaview.png"
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$DATA/icons/hicolor" || true

command -v update-mime-database >/dev/null 2>&1 && update-mime-database "$MIME" || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" || true

echo "kimbaview ist registriert (Exec=$BIN %f)."
echo "Optional als Standard festlegen:  xdg-mime default kimbaview.desktop text/markdown text/x-mediawiki"
