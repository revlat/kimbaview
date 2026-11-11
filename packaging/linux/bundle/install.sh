#!/bin/sh
# kimbaview – Installation für Linux (aktueller Benutzer, ohne Root-Rechte)
#
#   tar xzf kimbaview-<version>-linux.tar.gz
#   cd kimbaview-<version>-linux && ./install.sh
#
# Legt eine eigene Python-Umgebung unter ~/.local/share/kimbaview an, verlinkt den
# Befehl nach ~/.local/bin/kimbaview und trägt kimbaview ins Startmenü und unter
# „Öffnen mit“ ein. Entfernen: ./uninstall.sh
# Meldungen auf Deutsch, wenn die Systemsprache Deutsch ist, sonst auf Englisch.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PYTHON:-python3}
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
PREFIX="$DATA/kimbaview"
BINDIR="$HOME/.local/bin"

case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
    de*) DE=1 ;;
    *) DE=0 ;;
esac
# msg "englischer Text" "deutscher Text"
msg() { if [ "$DE" = 1 ]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }
fail() { if [ "$DE" = 1 ]; then printf 'FEHLER: %s\n' "$2" >&2; else printf 'ERROR: %s\n' "$1" >&2; fi; exit 1; }

hint_packages() {
    msg "" ""
    msg "Please install the system packages first (needs Python 3.10+, e.g. from" \
        "Bitte zuerst die Systempakete installieren (benötigt Python 3.10+, z. B. ab"
    msg "Ubuntu 22.04, Debian 12, Fedora 36, Linux Mint 21):" \
        "Ubuntu 22.04, Debian 12, Fedora 36, Linux Mint 21):"
    printf '%s\n' "  Debian/Ubuntu:  sudo apt install python3 python3-venv python3-gi gir1.2-webkit2-4.1"
    printf '%s\n' "  Fedora:         sudo dnf install python3 python3-gobject webkit2gtk4.1"
    printf '%s\n' "  Arch/Manjaro:   sudo pacman -S python python-gobject webkit2gtk-4.1"
    printf '%s\n' "  openSUSE:       sudo zypper install python3 python3-gobject python3-gobject-Gdk typelib-1_0-WebKit2-4_1"
    msg "Optional for MediaWiki files: pandoc (same package manager)." \
        "Optional für MediaWiki-Dateien: pandoc (gleicher Paketmanager)."
}

# 1) Voraussetzungen prüfen
command -v "$PY" >/dev/null 2>&1 || { hint_packages; fail "Python 3 ($PY) not found." "Python 3 ($PY) nicht gefunden."; }
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    hint_packages
    FOUND=$("$PY" -c 'import sys; print(sys.version.split()[0])')
    fail "kimbaview needs Python 3.10 or newer, found: $FOUND" \
         "kimbaview braucht Python 3.10 oder neuer, gefunden: $FOUND"
fi
"$PY" -c 'import venv, ensurepip' 2>/dev/null || { hint_packages; fail "Python module venv/ensurepip is missing (package python3-venv)." "Python-Modul venv/ensurepip fehlt (Paket python3-venv)."; }
if ! "$PY" - <<'EOF' 2>/dev/null
import gi
for v in ("4.1", "4.0"):
    try:
        gi.require_version("WebKit2", v)
        break
    except ValueError:
        pass
else:
    raise SystemExit(1)
from gi.repository import WebKit2  # noqa: F401
EOF
then
    hint_packages
    fail "The web engine WebKitGTK (python3-gi + WebKit2) is not installed." \
         "Die Web-Engine WebKitGTK (python3-gi + WebKit2) ist nicht installiert."
fi
ls "$HERE"/wheelhouse/kimbaview-*.whl >/dev/null 2>&1 || fail "wheelhouse/ is missing or incomplete." "wheelhouse/ fehlt oder ist unvollständig."

# 2) Eigene Umgebung anlegen (nutzt gi/WebKit aus dem System)
msg "Installing to $PREFIX …" "Installiere nach $PREFIX …"
rm -rf "$PREFIX/venv"
mkdir -p "$PREFIX"
"$PY" -m venv --system-site-packages "$PREFIX/venv"
PIP="$PREFIX/venv/bin/pip"
if ! "$PIP" install --quiet --no-index --find-links "$HERE/wheelhouse" kimbaview; then
    msg "Offline installation not possible (different Python version/architecture?) – downloading dependencies …" \
        "Offline-Installation nicht möglich (andere Python-Version/Architektur?) – lade Abhängigkeiten aus dem Internet …"
    "$PIP" install --quiet --find-links "$HERE/wheelhouse" kimbaview
fi
"$PREFIX/venv/bin/kimbaview" --selftest >/dev/null || fail "Self-test failed: $PREFIX/venv/bin/kimbaview --selftest" "Selbsttest fehlgeschlagen: $PREFIX/venv/bin/kimbaview --selftest"

# 3) Befehl verfügbar machen
mkdir -p "$BINDIR"
ln -sf "$PREFIX/venv/bin/kimbaview" "$BINDIR/kimbaview"

# 4) Startmenü und „Öffnen mit“
KIMBAVIEW_BIN="$PREFIX/venv/bin/kimbaview" sh "$HERE/desktop/install.sh"

msg "" ""
msg "Done. Start it from the application menu, via right-click → \"Open with\" or in a terminal:  kimbaview file.md" \
    "Fertig. Start über das Startmenü, per Rechtsklick → „Öffnen mit“ oder im Terminal:  kimbaview datei.md"
case ":$PATH:" in
    *":$BINDIR:"*) ;;
    *) msg "Note: $BINDIR is not in PATH. For the terminal command, add to ~/.profile:  export PATH=\"\$HOME/.local/bin:\$PATH\"" \
           "Hinweis: $BINDIR ist nicht im PATH. Für den Terminal-Befehl ggf. in ~/.profile ergänzen:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;;
esac
command -v pandoc >/dev/null 2>&1 || msg "Note: for MediaWiki files please also install 'pandoc' (Markdown works without it)." \
                                         "Hinweis: Für MediaWiki-Dateien bitte noch 'pandoc' installieren (Markdown geht auch ohne)."
