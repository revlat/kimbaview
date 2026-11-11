"""Bilder im bereits bereinigten HTML behandeln.

* Externe Bilder (http/https) werden nicht geladen, sondern als Platzhalter
  mit ihrer Adresse angezeigt.
* Lokale Bilder werden – nach strenger Pfadprüfung (paths.py) – als
  data:-URI eingebettet. Dadurch braucht das Fenster weder Dateizugriff noch
  einen lokalen Server, und die CSP kann ``img-src data:`` bleiben.

Achtung: Diese Funktion arbeitet auf der Ausgabe von ``sanitize_html``. Sie
baut jedes <img> komplett neu auf (alle Werte escaped); andere Tags bleiben
unverändert.
"""

from __future__ import annotations

import base64
import html as html_mod
import re
import threading
from pathlib import Path

from kimbaview.i18n import t
from kimbaview.paths import resolve_local_resource
from kimbaview.sanitize import TAG_RE

MAX_IMAGE_SIZE = 10 * 1024 * 1024       # pro Bild
MAX_TOTAL_IMAGE_SIZE = 40 * 1024 * 1024  # pro Rendervorgang

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    # SVG in <img> führt keine Skripte aus und lädt keine externen Ressourcen.
    ".svg": "image/svg+xml",
}

_ATTR_RE = re.compile(r'([^\s"\'>/=]+)(?:="([^"]*)")?')


def _esc(value: str) -> str:
    return html_mod.escape(value, quote=True)


def _placeholder(kind: str, label: str, detail: str) -> str:
    return (
        f'<span class="wv-img-placeholder wv-img-{kind}" title="{_esc(detail)}">'
        f'{_esc(label)} <code>{_esc(detail)}</code></span>'
    )


class ImageInliner:
    """Bettet Bilder ein; merkt sich bereits gelesene Dateien (pro Dokument)."""

    def __init__(self, base_dir: str | Path, root: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir)
        # Bilder werden relativ zum Dokument aufgelöst, müssen aber im Wurzelordner liegen.
        self.root = Path(root) if root is not None else self.base_dir
        self._cache: dict[tuple[str, int, int], str] = {}
        self._lock = threading.Lock()

    def _data_uri(self, path: Path) -> str | None:
        mime = IMAGE_TYPES.get(path.suffix.lower())
        if mime is None:
            return None
        st = path.stat()
        if st.st_size > MAX_IMAGE_SIZE:
            return None
        key = (str(path), st.st_mtime_ns, st.st_size)
        with self._lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached
        with open(path, "rb") as fh:
            data = fh.read(MAX_IMAGE_SIZE + 1)
        if len(data) > MAX_IMAGE_SIZE:
            return None
        uri = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
        with self._lock:
            # alte Versionen derselben Datei verwerfen, Cache klein halten
            self._cache = {k: v for k, v in self._cache.items() if k[0] != key[0]}
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[key] = uri
        return uri

    def process(self, html: str) -> str:
        budget = [MAX_TOTAL_IMAGE_SIZE]

        def repl(m: re.Match[str]) -> str:
            if m.group(1).lower() != "img":
                return m.group(0)
            attrs = {
                k.lower(): html_mod.unescape(v or "") for k, v in _ATTR_RE.findall(m.group(2))
            }
            src = attrs.get("src", "").strip()
            alt = attrs.get("alt", "")
            title = attrs.get("title", "")
            if not src:
                return _placeholder("missing", t("img.missing"), alt or t("img.no_description"))
            low = src.lower()
            if low.startswith(("http://", "https://")):
                return _placeholder("external", t("img.external"), src)
            path = resolve_local_resource(self.base_dir, src, root=self.root)
            if path is None:
                return _placeholder(
                    "blocked", t("img.blocked"), src
                )
            try:
                uri = self._data_uri(path)
            except OSError:
                uri = None
            if uri is None:
                return _placeholder("blocked", t("img.unsupported"), src)
            budget[0] -= len(uri)
            if budget[0] < 0:
                return _placeholder("blocked", t("img.budget"), src)
            out = f'<img src="{uri}" alt="{_esc(alt)}"'
            if title:
                out += f' title="{_esc(title)}"'
            for dim in ("width", "height"):
                val = attrs.get(dim, "")
                if val.isdigit() and len(val) <= 5:
                    out += f' {dim}="{val}"'
            return out + ">"

        return TAG_RE.sub(repl, html)


def inline_images(html: str, base_dir: str | Path) -> str:
    return ImageInliner(base_dir).process(html)

