#!/bin/sh
# Baut dist/kimbaview-<version>-linux.tar.gz (für die Build-Pipeline oder lokal).
# Aufruf im Projektordner:  sh packaging/linux/build-bundle.sh [python]
# Am besten mit der ältesten unterstützten Python-Version (3.10) bauen, damit die
# Abhängigkeiten (abi3/py3-Wheels) auch mit neueren Versionen funktionieren.
set -eu

PY=${1:-python3}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
VERSION=$("$PY" -c 'import sys; sys.path.insert(0, "src"); import kimbaview; print(kimbaview.__version__)')
NAME="kimbaview-$VERSION-linux"
OUT="$ROOT/build/$NAME"

rm -rf "$OUT"
mkdir -p "$OUT/wheelhouse" "$OUT/desktop" "$ROOT/dist"

# kimbaview + alle Abhängigkeiten als Wheels (offline installierbar)
"$PY" -m pip wheel --quiet --wheel-dir "$OUT/wheelhouse" .

cp packaging/linux/bundle/install.sh packaging/linux/bundle/uninstall.sh "$OUT/"
cp packaging/linux/install.sh packaging/linux/uninstall.sh \
   packaging/linux/kimbaview.desktop packaging/linux/kimbaview-mediawiki.xml \
   packaging/linux/kimbaview.png "$OUT/desktop/"
chmod 755 "$OUT/install.sh" "$OUT/uninstall.sh" "$OUT/desktop/install.sh" "$OUT/desktop/uninstall.sh"
cp LICENSE "$OUT/LICENSE.txt"
cp README.md README.de.md "$OUT/"
cp -R docs "$OUT/docs"
"$PY" packaging/collect_licenses.py "$OUT/THIRD-PARTY-LICENSES.txt"

tar -C "$ROOT/build" -czf "$ROOT/dist/$NAME.tar.gz" "$NAME"
echo "Fertig: dist/$NAME.tar.gz"
