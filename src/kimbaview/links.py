"""Prüfung externer Links und Absicherung von ``webbrowser.open``.

pywebview öffnet Links, die ein neues Fenster anfordern (target=_blank,
Mittelklick, Strg+Klick), per ``webbrowser.open`` im Standardbrowser – und
zwar unabhängig vom URL-Schema. Wir ersetzen ``webbrowser.open`` deshalb
prozessweit durch eine Variante, die ausschließlich http/https zulässt.
Das ist die letzte, Python-seitige Verteidigungslinie; zuvor entfernen der
Sanitizer und das eigene Klick-Skript bereits alle anderen Schemata.
"""

from __future__ import annotations

import logging
import webbrowser
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_URL_LENGTH = 8192


def is_safe_external_url(url: object) -> bool:
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        return False
    # Steuer- und Leerzeichen sind in einer gültigen absoluten URL nicht nötig
    # und werden für Verschleierungen (java\tscript:) benutzt.
    if any(ord(ch) <= 0x20 or ord(ch) == 0x7F for ch in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme.lower() in ALLOWED_SCHEMES and bool(parts.hostname)


_installed = False


def install_browser_guard() -> None:
    """Ersetzt webbrowser.open/open_new/open_new_tab durch geprüfte Varianten."""
    global _installed
    if _installed:
        return
    original_open = webbrowser.open

    def guarded_open(url, new=0, autoraise=True):
        if not is_safe_external_url(url):
            log.warning("Link mit nicht erlaubtem Schema ignoriert: %.200r", url)
            return False
        return original_open(url, new, autoraise)

    webbrowser.open = guarded_open
    webbrowser.open_new = lambda url: guarded_open(url, 1)
    webbrowser.open_new_tab = lambda url: guarded_open(url, 2)
    _installed = True
