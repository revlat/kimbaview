"""Die HTML-Hülle des Fensters (einmal geladen) und das Update-Skript.

Die Hülle enthält eine strenge Content-Security-Policy. Erlaubt sind nur
das eigene Stylesheet und das eigene Skript (beide per Nonce) sowie Bilder
als data:-URI. Inhalte werden später per ``update_script`` hineingeschoben.
"""

from __future__ import annotations

import html as html_mod
import json
import secrets
from functools import lru_cache
from importlib.resources import files

from kimbaview.highlight import pygments_css
from kimbaview.i18n import get_language, t
from kimbaview.settings import DEFAULT_WIDTH, WIDTH_STEPS, valid_width


def new_nonce() -> str:
    return secrets.token_urlsafe(18)


def content_security_policy(nonce: str) -> str:
    return "; ".join(
        [
            "default-src 'none'",
            f"script-src 'nonce-{nonce}'",
            f"style-src 'nonce-{nonce}'",
            "img-src data:",
            "font-src 'none'",
            "connect-src 'none'",
            "media-src 'none'",
            "object-src 'none'",
            "frame-src 'none'",
            "child-src 'none'",
            "worker-src 'none'",
            "manifest-src 'none'",
            "form-action 'none'",
            "base-uri 'none'",
        ]
    )


@lru_cache(maxsize=None)
def _asset(name: str) -> str:
    return files("kimbaview").joinpath("assets", name).read_text(encoding="utf-8")


def build_shell(title: str, nonce: str, text_width: int = DEFAULT_WIDTH) -> str:
    width = valid_width(text_width)
    width = DEFAULT_WIDTH if width is None else width
    csp = html_mod.escape(content_security_policy(nonce), quote=True)
    css = _asset("style.css") + "\n" + pygments_css()
    js = (
        _asset("viewer.js")
        .replace("/*WIDTH_STEPS*/", json.dumps(list(WIDTH_STEPS)))
        .replace("/*FULL_LABEL*/", json.dumps(t("ui.full_label"), ensure_ascii=True))
    )
    e = lambda key: html_mod.escape(t(key), quote=True)  # noqa: E731
    cs = e("ui.key_ctrl_shift")
    n = html_mod.escape(nonce, quote=True)
    return f"""<!DOCTYPE html>
<html lang="{get_language()}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_mod.escape(title)}</title>
<style nonce="{n}">
{css}
</style>
</head>
<body>
<div id="wv-notice" class="wv-notice" role="status" aria-live="polite" hidden></div>
<main id="wv-content" class="wv-doc" data-wv-width="{width}"><p class="wv-loading">{e('ui.loading')}</p></main>
<div id="wv-toast" class="wv-toast" role="alert" hidden></div>
<div id="wv-toolbar" class="wv-toolbar" role="toolbar" aria-label="{e('ui.toolbar')}">
<span id="wv-navgroup" class="wv-navgroup" hidden>
<button type="button" id="wv-back" title="{e('ui.back')} (Alt+←)" aria-label="{e('ui.back')}" disabled>‹</button>
<button type="button" id="wv-forward" title="{e('ui.forward')} (Alt+→)" aria-label="{e('ui.forward')}" disabled>›</button>
<span class="wv-sep"></span>
</span>
<button type="button" id="wv-narrower" title="{e('ui.narrower')} ({cs}+←)" aria-label="{e('ui.narrower')}">−</button>
<span id="wv-width-label" class="wv-width-label" aria-live="polite"></span>
<button type="button" id="wv-wider" title="{e('ui.wider')} ({cs}+→)" aria-label="{e('ui.wider')}">+</button>
<button type="button" id="wv-full" title="{e('ui.full_toggle')} ({cs}+F)" aria-label="{e('ui.full')}" aria-pressed="false">↔</button>
</div>
<script nonce="{n}">
{js}
</script>
</body>
</html>
"""


def update_script(payload: dict) -> str:
    """JavaScript, das ein Update-Payload an das Fenster übergibt.

    Der Payload wird als JSON-Literal eingebettet (ensure_ascii → keine
    Sonderfälle mit Zeilentrennern), es wird kein HTML in Code verwandelt.
    """
    data = json.dumps(payload, ensure_ascii=True)
    return f"window.__kimbaview && window.__kimbaview.update({data});"
