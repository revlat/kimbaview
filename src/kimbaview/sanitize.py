"""HTML-Bereinigung mit nh3 (Allowlist) für beide Formate.

Grundsätze
* Nur ausdrücklich erlaubte Tags/Attribute/Klassen bleiben erhalten.
* Skripte, Styles, iframes, Objekte usw. werden samt Inhalt entfernt.
* Event-Handler-Attribute (on*) sind nie erlaubt.
* URLs in href/src: nur http/https oder relativ (javascript:, data:, file: … fliegen raus).
* Alle ``id``-Attribute bekommen das Präfix ``wv-u-`` (und #-Links entsprechend),
  damit Dokumentinhalte keine Elemente/Globals der Oberfläche überdecken können
  (DOM-Clobbering).
* ``style`` wird nur für ``text-align`` in Tabellenzellen zugelassen und danach in
  eine CSS-Klasse umgewandelt, sodass die Content-Security-Policy keine
  Inline-Styles erlauben muss.
"""

from __future__ import annotations

import re

import nh3

from kimbaview.highlight import CODE_CLASS, token_classes

ID_PREFIX = "wv-u-"
TEMPLATE_CLASS = "wv-template"

ALLOWED_TAGS = frozenset(
    {
        "a", "abbr", "b", "bdi", "bdo", "blockquote", "br", "caption", "cite", "code",
        "col", "colgroup", "dd", "del", "details", "dfn", "div", "dl", "dt", "em",
        "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img",
        "input", "ins", "kbd", "li", "mark", "ol", "p", "pre", "q", "rp", "rt", "ruby",
        "s", "samp", "section", "small", "span", "strike", "strong", "sub", "summary",
        "sup", "table", "tbody", "td", "tfoot", "th", "thead", "time", "tr", "tt", "u",
        "ul", "var", "wbr",
    }
)

# Diese Tags werden einschließlich ihres Inhalts entfernt.
CLEAN_CONTENT_TAGS = frozenset(
    {
        "script", "style", "iframe", "frame", "frameset", "object", "embed", "applet",
        "noscript", "noembed", "noframes", "template", "textarea", "select", "option",
        "title", "svg", "math", "audio", "video", "canvas", "button",
    }
)

ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"id", "title", "lang", "dir"},
    "a": {"href"},
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan", "style"},
    "th": {"colspan", "rowspan", "style", "scope"},
    "col": {"span"},
    "colgroup": {"span"},
    "ol": {"start", "reversed"},
    "li": {"value"},
    "input": {"checked"},
    "details": {"open"},
    "time": {"datetime"},
    "abbr": set(),
}

TAG_ATTRIBUTE_VALUES = {"input": {"type": {"checkbox"}}}
SET_TAG_ATTRIBUTE_VALUES = {
    # target=_blank: ein Klick auf http(s)-Links landet in pywebviews
    # "Neues Fenster"-Behandlung → geprüftes webbrowser.open (siehe links.py).
    "a": {"target": "_blank"},
    "input": {"disabled": "disabled"},
}

ALLOWED_CLASSES = {
    "span": set(token_classes()) | {TEMPLATE_CLASS},
    "pre": {CODE_CLASS},
    "section": {"footnotes"},
    "hr": {"footnotes-sep"},
    "ol": {"footnotes-list"},
    "ul": {"contains-task-list"},
    "li": {"footnote-item", "task-list-item"},
    "sup": {"footnote-ref"},
    "a": {"footnote-backref", "footnote-ref", "wikilink"},
    "input": {"task-list-item-checkbox"},
}


_URL_HEAD_RE = re.compile(r"[/?#]")


def _suspicious_relative(v: str) -> bool:
    """Relative URL, die wie ein (verschleiertes) Schema aussieht, z. B. ``jav%09ascript:``."""
    low = v.lower()
    if low.startswith(("http://", "https://")):
        return False
    if low.startswith("//"):  # protokoll-relativ → fremder Host
        return True
    head = _URL_HEAD_RE.split(low, 1)[0]
    return ":" in head or "%3a" in head or "\\" in v


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if attr == "id":
        return ID_PREFIX + value
    if (tag == "a" and attr == "href") or (tag == "img" and attr == "src"):
        v = value.strip()
        if tag == "a" and v.startswith("#"):
            return "#" + ID_PREFIX + v[1:]
        if _suspicious_relative(v):
            return None
    return value


# Serialisierte nh3-Ausgabe: Attributwerte stehen immer in "…" und enthalten kein
# rohes ", daher lässt sich ein Start-Tag robust mit diesem Muster erkennen.
TAG_RE = re.compile(r'<([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^\s"\'>/=]+(?:="[^"]*")?)*)\s*/?>')
_STYLE_ALIGN_RE = re.compile(r'\sstyle="text-align:\s*(left|right|center)\s*;?\s*"')
_STYLE_ANY_RE = re.compile(r'\sstyle="[^"]*"')


def _convert_alignment(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        tag = m.group(0)
        if m.group(1).lower() == "input" and ' type="checkbox"' not in tag:
            return ""  # nur Task-Listen-Checkboxen behalten
        if " style=" not in tag:
            return tag
        tag = _STYLE_ALIGN_RE.sub(lambda s: f' class="wv-align-{s.group(1)}"', tag)
        return _STYLE_ANY_RE.sub("", tag)

    return TAG_RE.sub(repl, html)


def sanitize_html(html: str) -> str:
    cleaned = nh3.clean(
        html,
        tags=set(ALLOWED_TAGS),
        clean_content_tags=set(CLEAN_CONTENT_TAGS),
        attributes={k: set(v) for k, v in ALLOWED_ATTRIBUTES.items()},
        attribute_filter=_attribute_filter,
        strip_comments=True,
        link_rel="noopener noreferrer",
        generic_attribute_prefixes=set(),
        tag_attribute_values=TAG_ATTRIBUTE_VALUES,
        set_tag_attribute_values=SET_TAG_ATTRIBUTE_VALUES,
        url_schemes={"http", "https"},
        allowed_classes={k: set(v) for k, v in ALLOWED_CLASSES.items()},
        filter_style_properties={"text-align"},
    )
    return _convert_alignment(cleaned)
