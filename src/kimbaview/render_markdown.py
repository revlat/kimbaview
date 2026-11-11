"""Markdown → HTML mit markdown-it-py (Tabellen, Fußnoten, Task-Listen, Durchstreichen).

Rohes HTML im Markdown ist erlaubt, wird aber anschließend von sanitize.py
bereinigt. Die Ausgabe dieses Moduls ist deshalb *nie* direkt vertrauenswürdig.
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

from kimbaview.highlight import highlight_code


def _highlight(code: str, lang: str, _attrs: str) -> str:
    return highlight_code(code, lang)


def _make_parser() -> MarkdownIt:
    md = MarkdownIt(
        "commonmark",
        {"html": True, "linkify": False, "typographer": False, "highlight": _highlight},
    )
    md.enable(["table", "strikethrough"])
    md.use(footnote_plugin)
    md.use(tasklists_plugin)
    md.use(anchors_plugin, min_level=1, max_level=6)
    return md


def render_markdown(text: str) -> str:
    # Eigene Instanz pro Aufruf: mehrere Fenster/Threads stören sich nicht.
    return _make_parser().render(text)
