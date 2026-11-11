"""Kleine, robuste Einstellungsdatei (derzeit nur die Textbreite).

Ort:  Windows  %APPDATA%\\kimbaview\\settings.json
      macOS    ~/Library/Application Support/kimbaview/settings.json
      Linux    $XDG_CONFIG_HOME/kimbaview/settings.json (Standard ~/.config/…)

Gelesene Werte werden streng geprüft; eine kaputte oder manipulierte Datei
führt nur dazu, dass die Standardwerte gelten.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

WIDTH_STEPS = (600, 700, 800, 900, 1000, 1200, 1400, 0)  # 0 = volle Fensterbreite
DEFAULT_WIDTH = 800
MAX_SETTINGS_SIZE = 64 * 1024


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "kimbaview"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "kimbaview"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "kimbaview"


def valid_width(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value in WIDTH_STEPS else None


def load_settings(path: Path | None = None) -> dict:
    path = path or config_dir() / "settings.json"
    settings = {"width": DEFAULT_WIDTH}
    try:
        if path.stat().st_size > MAX_SETTINGS_SIZE:
            return settings
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if isinstance(data, dict):
        w = valid_width(data.get("width"))
        if w is not None:
            settings["width"] = w
    return settings


def save_settings(settings: dict, path: Path | None = None) -> None:
    path = path or config_dir() / "settings.json"
    w = valid_width(settings.get("width"))
    if w is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".settings-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"width": w}, fh)
        os.replace(tmp, path)  # atomar
    except OSError:
        log.debug("Einstellungen konnten nicht gespeichert werden", exc_info=True)
