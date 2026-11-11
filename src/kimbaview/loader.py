"""Tolerantes, größenbegrenztes Einlesen von Textdateien."""

from __future__ import annotations

import os
from pathlib import Path

from kimbaview.i18n import t

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class FileTooLargeError(Exception):
    def __init__(self, size: int, limit: int = MAX_FILE_SIZE) -> None:
        self.size = size
        self.limit = limit
        super().__init__(t("file.too_large", size=size / 1024 / 1024, limit=limit // 1024 // 1024))


def read_text_file(path: str | Path, max_size: int = MAX_FILE_SIZE) -> str:
    """Liest eine Datei als UTF-8; ungültige Bytes werden zu U+FFFD.

    Die Größe wird sowohl vor dem Lesen (fstat) als auch beim Lesen geprüft,
    damit eine während des Lesens wachsende Datei das Limit nicht umgeht.
    """
    with open(path, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        if size > max_size:
            raise FileTooLargeError(size, max_size)
        data = fh.read(max_size + 1)
    if len(data) > max_size:
        raise FileTooLargeError(len(data), max_size)
    # utf-8-sig entfernt ein eventuelles BOM; errors="replace" verhindert Abstürze.
    return data.decode("utf-8-sig", errors="replace")
