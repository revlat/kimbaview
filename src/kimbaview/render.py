"""Gemeinsame Render-Pipeline: Format → rohes HTML → Sanitizer → Bilder."""

from __future__ import annotations

from pathlib import Path

from kimbaview.formats import MARKDOWN, MEDIAWIKI
from kimbaview.images import ImageInliner
from kimbaview.render_markdown import render_markdown
from kimbaview.render_mediawiki import render_mediawiki
from kimbaview.sanitize import sanitize_html


def render_raw(text: str, fmt: str) -> str:
    if fmt == MARKDOWN:
        return render_markdown(text)
    if fmt == MEDIAWIKI:
        return render_mediawiki(text)
    raise ValueError(f"Unbekanntes Format: {fmt!r}")


def render_document(
    text: str, fmt: str, base_dir: str | Path, inliner: ImageInliner | None = None
) -> str:
    """Liefert bereinigtes, sicher anzeigbares HTML (Fragment)."""
    safe = sanitize_html(render_raw(text, fmt))
    return (inliner or ImageInliner(base_dir)).process(safe)
