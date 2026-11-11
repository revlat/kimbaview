"""Erkennung des Dateiformats anhand der Endung (oder per --format)."""

from __future__ import annotations

from pathlib import Path

from kimbaview.i18n import t

MARKDOWN = "md"
MEDIAWIKI = "mediawiki"
FORMATS = (MARKDOWN, MEDIAWIKI)

EXTENSIONS: dict[str, str] = {
    ".md": MARKDOWN,
    ".markdown": MARKDOWN,
    ".mediawiki": MEDIAWIKI,
    ".wiki": MEDIAWIKI,
    ".wikitext": MEDIAWIKI,
}


class UnknownFormatError(ValueError):
    """Die Dateiendung ist keinem Format zugeordnet."""


def detect_format(path: str | Path, override: str | None = None) -> str:
    """Liefert ``"md"`` oder ``"mediawiki"``.

    ``override`` (aus ``--format``) hat Vorrang vor der Endung.
    """
    if override is not None:
        value = override.strip().lower()
        if value not in FORMATS:
            raise UnknownFormatError(t("format.unknown_override", value=override))
        return value
    suffix = Path(path).suffix.lower()
    try:
        return EXTENSIONS[suffix]
    except KeyError:
        raise UnknownFormatError(
            t("format.unknown_extension", suffix=suffix or t("format.no_extension"))
        ) from None
