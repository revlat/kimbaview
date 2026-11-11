"""Links zwischen lokalen Dokumenten (ohne GUI testbar).

Sicherheitsregeln
* Geöffnet werden nur Dateien mit Dokument-Endung (.md, .markdown, .mediawiki,
  .wiki, .wikitext) – nie Programme, Bilder, PDFs o. Ä.
* Das Ziel muss nach vollständiger Auflösung (``..``, URL-Kodierung, Symlinks,
  Junctions) innerhalb des *Wurzelordners* liegen. Der Wurzelordner ist der
  Ordner der Datei, die der Benutzer ausdrücklich geöffnet hat (Kommandozeile,
  „Öffnen mit“, Dateidialog). Innerhalb davon sind auch Links nach oben erlaubt.
* Anfragen aus dem Fenster werden streng geprüft (Typ, Länge, erlaubte Werte).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from kimbaview.formats import EXTENSIONS, MARKDOWN, MEDIAWIKI
from kimbaview.i18n import t
from kimbaview.paths import resolve_local_resource

MAX_HREF = 4096
MAX_FRAGMENT = 200
_MD_EXTS = [e for e, f in EXTENSIONS.items() if f == MARKDOWN]
_WIKI_EXTS = [e for e, f in EXTENSIONS.items() if f == MEDIAWIKI]


class LinkError(Exception):
    """Link kann/darf nicht geöffnet werden; die Meldung ist für den Hinweis gedacht."""


@dataclass(frozen=True)
class NavRequest:
    action: str          # "open" | "back" | "forward"
    href: str = ""
    new_window: bool = False


@dataclass(frozen=True)
class LinkTarget:
    path: Path
    fragment: str | None


def parse_nav_request(value: object) -> NavRequest | None:
    """Prüft eine Anfrage aus dem Fenster. Ungültiges → None."""
    if not isinstance(value, dict):
        return None
    action = value.get("action")
    if action in ("back", "forward"):
        return NavRequest(action)
    if action != "open":
        return None
    href, mode = value.get("href"), value.get("mode", "same")
    if not isinstance(href, str) or not href or len(href) > MAX_HREF:
        return None
    if mode not in ("same", "new"):
        return None
    return NavRequest("open", href, mode == "new")


def _candidates(rel: str, current_fmt: str) -> list[str]:
    """Kandidaten für einen Link. Ohne Endung (z. B. [[Seite]]) werden die
    Dokument-Endungen ausprobiert, das aktuelle Format zuerst."""
    suffix = Path(rel).suffix.lower()
    if suffix in EXTENSIONS:
        return [rel]
    if suffix and not rel.endswith("/"):
        # andere Endung (.pdf, .exe, .png …) – nie öffnen
        return []
    exts = (_WIKI_EXTS + _MD_EXTS) if current_fmt == MEDIAWIKI else (_MD_EXTS + _WIKI_EXTS)
    names = [rel]
    if "_" in rel:
        names.append(rel.replace("_", " "))  # MediaWiki: Unterstrich = Leerzeichen
    return [n + e for n in names for e in exts]


def resolve_doc_link(current: Path, href: str, root: Path, current_fmt: str = MARKDOWN) -> LinkTarget:
    """Löst einen relativen Dokument-Link auf oder wirft LinkError."""
    try:
        parts = urlsplit(href.strip())
    except ValueError:
        raise LinkError(t("link.invalid")) from None
    if parts.scheme or parts.netloc:
        raise LinkError(t("link.not_local"))
    fragment = unquote(parts.fragment)[:MAX_FRAGMENT] or None
    rel = parts.path
    if not rel:
        raise LinkError(t("link.empty"))
    decoded = unquote(rel)
    cands = _candidates(decoded, current_fmt)
    if not cands:
        raise LinkError(
            t("link.not_document", name=decoded)
        )
    base = current.parent
    for cand in cands:
        # resolve_local_resource zerlegt/dekodiert selbst → Sonderzeichen wieder maskieren
        quoted = cand.replace("%", "%25").replace("#", "%23").replace("?", "%3F")
        target = resolve_local_resource(base, quoted, root=root)
        if target is not None and target.suffix.lower() in EXTENSIONS:
            return LinkTarget(target, fragment)
    # Unterscheiden: existiert, aber außerhalb – oder gar nicht vorhanden?
    try:
        outside = (base / cands[0]).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        outside = None
    if outside is not None:
        raise LinkError(
            t("link.outside", name=decoded)
        )
    raise LinkError(t("link.not_found", name=decoded))
