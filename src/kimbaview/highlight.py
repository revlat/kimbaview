"""Syntaxhervorhebung mit Pygments – serverseitig, also ohne JavaScript im Fenster."""

from __future__ import annotations

import html
from functools import lru_cache

from pygments import highlight as _pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.token import STANDARD_TYPES
from pygments.util import ClassNotFound

CODE_CLASS = "wv-code"
MAX_HIGHLIGHT_CHARS = 200_000  # größere Blöcke werden nur escaped (Rechenzeit begrenzen)

_FORMATTER = HtmlFormatter(nowrap=True)


def token_classes() -> frozenset[str]:
    """Alle CSS-Klassen, die Pygments für Tokens erzeugen kann (für die Allowlist)."""
    return frozenset(c for c in STANDARD_TYPES.values() if c)


def highlight_code(code: str, lang: str | None) -> str:
    """Erzeugt ``<pre class="wv-code"><code>…</code></pre>``."""
    body = None
    name = (lang or "").strip().split()[0].lower()[:40] if (lang or "").strip() else ""
    if name and len(code) <= MAX_HIGHLIGHT_CHARS:
        try:
            lexer = get_lexer_by_name(name, stripnl=False, ensurenl=False)
            body = _pyg_highlight(code, lexer, _FORMATTER)
        except ClassNotFound:
            body = None
        except Exception:  # Pygments darf das Rendern nie abbrechen
            body = None
    if body is None:
        body = html.escape(code, quote=False)
    return f'<pre class="{CODE_CLASS}"><code>{body}</code></pre>'


def _style_defs(style: str, fallback: str) -> str:
    try:
        fmt = HtmlFormatter(style=style)
    except ClassNotFound:
        fmt = HtmlFormatter(style=fallback)
    # Nur auf unsere Codeblöcke beschränken; Hintergrund setzt unser eigenes CSS.
    lines = [
        ln
        for ln in fmt.get_style_defs(f".{CODE_CLASS}").splitlines()
        if ln.startswith(f".{CODE_CLASS} .")
    ]
    return "\n".join(lines)


@lru_cache(maxsize=1)
def pygments_css() -> str:
    light = _style_defs("default", "default")
    dark = _style_defs("github-dark", "monokai")
    return (
        f"{light}\n"
        "@media (prefers-color-scheme: dark) {\n"
        f"{dark}\n"
        "}\n"
    )
