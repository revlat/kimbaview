"""py2app-Build für macOS:  kimbaview.app mit Dateitypen für "Öffnen mit".

Empfohlen: sh packaging/macos/build-dmg.sh  (baut App + DMG, signiert falls eingerichtet)

Direkt (im Projektordner, auf einem Mac):
    python3 -m venv .venv && source .venv/bin/activate
    pip install . py2app          # NICHT -e: py2app findet editierbare Installationen schlecht
    python packaging/macos/setup_py2app.py py2app
Ergebnis: dist/kimbaview.app  →  nach /Applications oder ~/Applications kopieren.

Die App trägt sich mit LSHandlerRank "Alternate" ein: Sie erscheint im
Finder unter "Öffnen mit", wird aber nicht ungefragt zum Standardprogramm.
"""

import os
import sys

from setuptools import setup

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
# Bewusst NICHT im Projektordner arbeiten: setuptools würde sonst die
# Abhängigkeiten aus pyproject.toml übernehmen, und py2app bricht dann mit
# "install_requires is no longer supported" ab.
os.chdir(HERE)

from kimbaview import __version__  # noqa: E402

# Lizenzen ins App-Bundle (Contents/Resources) legen
import subprocess  # noqa: E402

os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
THIRD_PARTY = os.path.join(ROOT, "build", "THIRD-PARTY-LICENSES.txt")
subprocess.run(
    [sys.executable, os.path.join(ROOT, "packaging", "collect_licenses.py"), THIRD_PARTY], check=True
)

MARKDOWN_UTI = "net.daringfireball.markdown"
MEDIAWIKI_UTI = "org.mediawiki.wikitext"

PLIST = {
    "CFBundleName": "kimbaview",
    "CFBundleDisplayName": "kimbaview",
    "CFBundleIdentifier": "org.kimbaview.viewer",
    "CFBundleShortVersionString": __version__,
    "CFBundleVersion": __version__,
    "LSMinimumSystemVersion": "11.0",
    "NSHighResolutionCapable": True,
    "NSHumanReadableCopyright": "Copyright © 2026 revlat – MIT License",
    "CFBundleDevelopmentRegion": "en",
    "CFBundleLocalizations": ["en", "de"],
    "CFBundleDocumentTypes": [
        {
            "CFBundleTypeName": "Markdown document",
            "CFBundleTypeRole": "Viewer",
            "LSHandlerRank": "Alternate",
            "LSItemContentTypes": [MARKDOWN_UTI],
            "CFBundleTypeExtensions": ["md", "markdown"],
        },
        {
            "CFBundleTypeName": "MediaWiki document",
            "CFBundleTypeRole": "Viewer",
            "LSHandlerRank": "Alternate",
            "LSItemContentTypes": [MEDIAWIKI_UTI],
            "CFBundleTypeExtensions": ["mediawiki", "wiki", "wikitext"],
        },
    ],
    # Typen "importieren": kimbaview besitzt sie nicht, beschreibt sie aber,
    # falls kein anderes Programm sie bereits deklariert.
    "UTImportedTypeDeclarations": [
        {
            "UTTypeIdentifier": MARKDOWN_UTI,
            "UTTypeDescription": "Markdown document",
            "UTTypeConformsTo": ["public.plain-text"],
            "UTTypeTagSpecification": {
                "public.filename-extension": ["md", "markdown"],
                "public.mime-type": ["text/markdown"],
            },
        },
        {
            "UTTypeIdentifier": MEDIAWIKI_UTI,
            "UTTypeDescription": "MediaWiki document",
            "UTTypeConformsTo": ["public.plain-text"],
            "UTTypeTagSpecification": {
                "public.filename-extension": ["mediawiki", "wiki", "wikitext"],
                "public.mime-type": ["text/x-mediawiki"],
            },
        },
    ],
}

OPTIONS = {
    # Wandelt das "Datei öffnen"-AppleEvent beim Start in sys.argv um.
    "argv_emulation": True,
    "iconfile": os.path.join(ROOT, "packaging", "macos", "kimbaview.icns"),
    "plist": PLIST,
    "packages": ["kimbaview", "webview", "pygments", "markdown_it", "mdit_py_plugins", "watchdog"],
    "includes": ["nh3"],
    # Pillow wird nur von Pygments' (ungenutztem) Bild-Formatter optional importiert
    "excludes": ["PIL", "tkinter"],
    "resources": [os.path.join(ROOT, "LICENSE"), THIRD_PARTY,
                  os.path.join(HERE, "en.lproj"), os.path.join(HERE, "de.lproj")],
    "dist_dir": os.path.join(ROOT, "dist"),
    "bdist_base": os.path.join(ROOT, "build", "py2app"),
}

setup(
    name="kimbaview",
    version=__version__,
    app=[os.path.join(ROOT, "packaging", "launcher.py")],
    options={"py2app": OPTIONS},
)
