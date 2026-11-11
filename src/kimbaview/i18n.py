"""Sprachen der Oberfläche: Englisch (Standard) und Deutsch.

Die Sprache richtet sich nach der Systemsprache (Deutsch bei deutschem System,
sonst Englisch). Überschreiben: Kommandozeile ``--lang en|de`` oder
Umgebungsvariable ``KIMBAVIEW_LANG``.
"""

from __future__ import annotations

import locale
import os
import subprocess
import sys

LANGUAGES = ("en", "de")
DEFAULT = "en"

_current: str | None = None


def _system_language() -> str:
    """Ermittelt die Sprache der Benutzeroberfläche des Systems ("de" oder "en")."""
    try:
        if sys.platform == "win32":
            import ctypes

            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "de" if (langid & 0x3FF) == 0x07 else DEFAULT
        if sys.platform == "darwin":
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleLanguages"],
                capture_output=True, text=True, timeout=3,
            ).stdout
            first = out.replace("(", "").replace('"', "").split(",")[0].strip().lower()
            if first:
                return "de" if first.startswith("de") else DEFAULT
    except Exception:
        pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(var, "")
        if value:
            return "de" if value.lower().startswith("de") else DEFAULT
    try:
        loc = (locale.getlocale()[0] or "").lower()
        if loc.startswith("de") or loc.startswith("german"):
            return "de"
    except Exception:
        pass
    return DEFAULT


def normalize(lang: str | None) -> str | None:
    if not lang:
        return None
    lang = lang.strip().lower()[:2]
    return lang if lang in LANGUAGES else None


def set_language(lang: str | None = None) -> str:
    """Setzt die Sprache; ohne Angabe: KIMBAVIEW_LANG, sonst Systemsprache."""
    global _current
    _current = normalize(lang) or normalize(os.environ.get("KIMBAVIEW_LANG")) or _system_language()
    return _current


def get_language() -> str:
    return _current or set_language()


def t(key: str, **kwargs) -> str:
    """Übersetzter Text für ``key`` in der aktuellen Sprache."""
    entry = MESSAGES[key]
    text = entry.get(get_language()) or entry[DEFAULT]
    return text.format(**kwargs) if kwargs else text


MESSAGES: dict[str, dict[str, str]] = {
    # --- Kommandozeile
    "cli.description": {
        "en": "Displays Markdown and MediaWiki files and updates them live.",
        "de": "Zeigt Markdown- und MediaWiki-Dateien gerendert an und aktualisiert sie live.",
    },
    "cli.files": {"en": "file(s) to open", "de": "zu öffnende Datei(en)"},
    "cli.files_meta": {"en": "file", "de": "datei"},
    "cli.format": {
        "en": "override the format detected from the file extension",
        "de": "Formaterkennung über die Dateiendung überschreiben",
    },
    "cli.lang": {
        "en": "language of the user interface (default: system language)",
        "de": "Sprache der Oberfläche (Standard: Systemsprache)",
    },
    "cli.debug": {"en": "log messages to stderr", "de": "Protokollausgabe auf stderr"},
    # --- Dateidialog
    "dialog.filter_docs": {
        "en": "Markdown and MediaWiki (*.md;*.markdown;*.mediawiki;*.wiki;*.wikitext)",
        "de": "Markdown und MediaWiki (*.md;*.markdown;*.mediawiki;*.wiki;*.wikitext)",
    },
    "dialog.filter_all": {"en": "All files (*.*)", "de": "Alle Dateien (*.*)"},
    # --- Formate und Dateien
    "format.unknown_override": {
        "en": "Unknown format: {value!r} (allowed: md, mediawiki)",
        "de": "Unbekanntes Format: {value!r} (erlaubt: md, mediawiki)",
    },
    "format.unknown_extension": {
        "en": "Unknown file extension {suffix!r}. "
              "Supported: .md, .markdown, .mediawiki, .wiki, .wikitext – or --format md|mediawiki.",
        "de": "Unbekannte Dateiendung {suffix!r}. "
              "Unterstützt: .md, .markdown, .mediawiki, .wiki, .wikitext – oder --format md|mediawiki.",
    },
    "format.no_extension": {"en": "(none)", "de": "(keine)"},
    "file.too_large": {
        "en": "The file is too large ({size:.1f} MB). For safety, only files up to {limit} MB are displayed.",
        "de": "Die Datei ist zu groß ({size:.1f} MB). Aus Sicherheitsgründen werden nur Dateien "
              "bis {limit} MB angezeigt.",
    },
    "file.missing": {
        "en": "The file was deleted, moved or renamed. Showing the last version – it will be "
              "reloaded automatically as soon as it reappears.",
        "de": "Die Datei wurde gelöscht, verschoben oder umbenannt. Angezeigt wird der letzte Stand – "
              "sobald sie wieder auftaucht, wird sie automatisch neu geladen.",
    },
    "file.not_found_body": {
        "en": "File not found: {path}\nkimbaview is waiting for it to appear.",
        "de": "Datei nicht gefunden: {path}\nkimbaview wartet, bis sie erscheint.",
    },
    "file.not_found": {"en": "File not found.", "de": "Datei nicht gefunden."},
    "file.unreadable": {
        "en": "The file cannot be read: {error}",
        "de": "Die Datei kann nicht gelesen werden: {error}",
    },
    # --- Rendern
    "render.unexpected": {"en": "Unexpected error: {error}", "de": "Unerwarteter Fehler: {error}"},
    "render.mediawiki_failed": {
        "en": "MediaWiki could not be converted: {error}",
        "de": "MediaWiki konnte nicht umgewandelt werden: {error}",
    },
    "render.too_deep": {
        "en": "Rendering error: the document is nested too deeply.",
        "de": "Fehler beim Rendern: Das Dokument ist zu tief verschachtelt.",
    },
    "render.error": {
        "en": "Rendering error ({kind}): {error}",
        "de": "Fehler beim Rendern ({kind}): {error}",
    },
    "render.keeping_last": {
        "en": " – showing the last working version.",
        "de": " – angezeigt wird der letzte funktionierende Stand.",
    },
    "watch.unavailable": {
        "en": "Live updates are not available: {error}",
        "de": "Live-Aktualisierung nicht verfügbar: {error}",
    },
    # --- Pandoc
    "pandoc.missing": {
        "en": "MediaWiki files need the program Pandoc, but it was not found.\n{how}\n"
              "Then restart kimbaview. Markdown files work without Pandoc.",
        "de": "MediaWiki-Dateien benötigen das Programm Pandoc, es wurde aber nicht gefunden.\n{how}\n"
              "Danach kimbaview neu starten. Markdown-Dateien funktionieren auch ohne Pandoc.",
    },
    "pandoc.how_windows": {
        "en": "Install on Windows:  winget install --id JohnMacFarlane.Pandoc\n"
              "or use the installer from https://pandoc.org/installing.html",
        "de": "Installation unter Windows:  winget install --id JohnMacFarlane.Pandoc\n"
              "oder Installer von https://pandoc.org/installing.html",
    },
    "pandoc.how_macos": {
        "en": "Install on macOS:  brew install pandoc\n"
              "or use the installer from https://pandoc.org/installing.html",
        "de": "Installation unter macOS:  brew install pandoc\n"
              "oder Installer von https://pandoc.org/installing.html",
    },
    "pandoc.how_linux": {
        "en": "Install on Linux, e.g.:  sudo apt install pandoc   |   sudo dnf install pandoc"
              "   |   sudo pacman -S pandoc",
        "de": "Installation unter Linux, z. B.:  sudo apt install pandoc   |   sudo dnf install pandoc"
              "   |   sudo pacman -S pandoc",
    },
    "pandoc.timeout": {
        "en": "Pandoc exceeded the time limit of {timeout:g} s and was stopped.",
        "de": "Pandoc hat das Zeitlimit von {timeout:g} s überschritten und wurde beendet.",
    },
    "pandoc.start_failed": {
        "en": "Pandoc could not be started: {error}",
        "de": "Pandoc konnte nicht gestartet werden: {error}",
    },
    "pandoc.failed": {
        "en": "Pandoc reported an error (code {code}): {error}",
        "de": "Pandoc meldet einen Fehler (Code {code}): {error}",
    },
    "template.title": {
        "en": "Template – not resolved by kimbaview",
        "de": "Vorlage – wird von kimbaview nicht aufgelöst",
    },
    # --- Bilder
    "img.missing": {"en": "Image without a valid source:", "de": "Bild ohne gültige Quelle:"},
    "img.no_description": {"en": "(no description)", "de": "(ohne Beschreibung)"},
    "img.external": {"en": "External image not loaded:", "de": "Externes Bild nicht geladen:"},
    "img.blocked": {
        "en": "Image not found or outside the document folder:",
        "de": "Bild nicht gefunden oder außerhalb des Dokumentordners:",
    },
    "img.unsupported": {
        "en": "Image not supported or too large:",
        "de": "Bild nicht unterstützt oder zu groß:",
    },
    "img.budget": {
        "en": "Image limit for this document reached:",
        "de": "Bildlimit für dieses Dokument erreicht:",
    },
    # --- Links
    "link.invalid": {"en": "Invalid link.", "de": "Ungültiger Link."},
    "link.not_local": {
        "en": "Only links to local Markdown or MediaWiki files are opened.",
        "de": "Nur Links auf lokale Markdown- oder MediaWiki-Dateien werden geöffnet.",
    },
    "link.empty": {"en": "Empty link.", "de": "Leerer Link."},
    "link.not_document": {
        "en": "“{name}” is not a Markdown or MediaWiki file and will not be opened.",
        "de": "„{name}“ ist keine Markdown- oder MediaWiki-Datei und wird nicht geöffnet.",
    },
    "link.outside": {
        "en": "“{name}” is outside the folder of the opened file and is not opened for security reasons.",
        "de": "„{name}“ liegt außerhalb des Ordners der geöffneten Datei und wird aus "
              "Sicherheitsgründen nicht geöffnet.",
    },
    "link.not_found": {"en": "Link target not found: {name}", "de": "Link-Ziel nicht gefunden: {name}"},
    # --- Fenster
    "ui.loading": {"en": "Loading …", "de": "Wird geladen …"},
    "ui.toolbar": {"en": "Navigation and text width", "de": "Navigation und Textbreite"},
    "ui.back": {"en": "Back", "de": "Zurück"},
    "ui.forward": {"en": "Forward", "de": "Vor"},
    "ui.narrower": {"en": "Narrower", "de": "Schmaler"},
    "ui.wider": {"en": "Wider", "de": "Breiter"},
    "ui.full": {"en": "Full width", "de": "Volle Breite"},
    "ui.full_toggle": {"en": "Full width on/off", "de": "Volle Breite ein/aus"},
    "ui.full_label": {"en": "full width", "de": "volle Breite"},
    "ui.key_ctrl_shift": {"en": "Ctrl+Shift", "de": "Strg+Umschalt"},
}
