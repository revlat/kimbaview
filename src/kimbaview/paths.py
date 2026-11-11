"""Sichere Auflösung lokaler Ressourcen (Bilder) relativ zur geöffneten Datei.

Regel: Es dürfen nur Dateien im Verzeichnis der geöffneten Datei oder in
dessen Unterordnern geladen werden. Pfade werden vollständig aufgelöst
(inklusive Symlinks und Windows-Junctions); alles außerhalb wird abgelehnt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit

_IS_WINDOWS = sys.platform == "win32"


def _norm(p: Path | str) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def is_within(base: Path, candidate: Path) -> bool:
    """True, wenn ``candidate`` gleich ``base`` ist oder darunter liegt (beide aufgelöst)."""
    b, c = _norm(base), _norm(candidate)
    try:
        return os.path.commonpath([b, c]) == b
    except ValueError:  # z. B. unterschiedliche Laufwerke unter Windows
        return False


def resolve_local_resource(
    base_dir: str | Path, ref: str, root: str | Path | None = None
) -> Path | None:
    """Löst einen relativen Verweis (z. B. ``bilder/a.png``) sicher auf.

    Der Verweis wird relativ zu ``base_dir`` aufgelöst und muss innerhalb von
    ``root`` liegen (Standard: ``base_dir`` selbst). Liefert den aufgelösten
    Pfad oder ``None``, wenn der Verweis absolut ist, ein Schema/Host enthält,
    nicht existiert, keine reguläre Datei ist oder (nach Auflösen von ``..``
    und Symlinks) außerhalb von ``root`` liegt.
    """
    if not ref or len(ref) > 4096:
        return None
    ref = ref.strip()
    try:
        parts = urlsplit(ref)
    except ValueError:
        return None
    if parts.scheme or parts.netloc:
        return None
    rel = unquote(parts.path)
    if not rel or "\x00" in rel:
        return None
    # Absolute Pfade (POSIX, UNC, Laufwerksbuchstaben) ablehnen.
    if rel.startswith(("/", "\\")) or os.path.isabs(rel):
        return None
    win = PureWindowsPath(rel)
    if win.drive or win.root:
        return None
    if _IS_WINDOWS and ":" in rel:  # NTFS Alternate Data Streams, Laufwerksangaben
        return None
    try:
        base_real = Path(base_dir).resolve(strict=True)
        root_real = Path(root).resolve(strict=True) if root is not None else base_real
        candidate = (base_real / rel).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    if not is_within(root_real, base_real) or not is_within(root_real, candidate):
        return None
    if not candidate.is_file():
        return None
    return candidate
