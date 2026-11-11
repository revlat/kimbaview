"""Fensterunabhängige Logik eines geöffneten Dokuments.

Der Controller liest, rendert und entscheidet, was angezeigt wird. Das
Ergebnis geht als kleines Dict an eine ``push``-Funktion (im Programm:
JavaScript-Update im Fenster; in Tests: eine Liste). Grundsätze:

* Bei jedem Fehler bleibt der letzte funktionierende Stand sichtbar; oben
  erscheint ein Hinweis. Ausnahmen verlassen ``reload`` nie.
* Gelöscht/umbenannt → Hinweis, letzter Stand bleibt; taucht die Datei
  wieder auf, wird neu geladen.
"""

from __future__ import annotations

import html as html_mod
import logging
import threading
from pathlib import Path
from typing import Callable

from kimbaview.i18n import t
from kimbaview.images import ImageInliner
from kimbaview.loader import FileTooLargeError, read_text_file
from kimbaview.render import render_document
from kimbaview.render_mediawiki import PandocError, PandocNotFoundError

log = logging.getLogger(__name__)

Payload = dict


def _message_html(text: str) -> str:
    paras = "".join(f"<p>{html_mod.escape(p)}</p>" for p in text.split("\n") if p.strip())
    return f'<div class="wv-message">{paras}</div>'


class DocumentController:
    def __init__(
        self,
        path: str | Path,
        fmt: str,
        push: Callable[[Payload], None],
        renderer: Callable[..., str] = render_document,
        root: str | Path | None = None,
    ) -> None:
        self.path = Path(path).absolute()
        self.fmt = fmt
        self._push = push
        self._render = renderer
        self._inliner = ImageInliner(self.path.parent, root)
        self._lock = threading.Lock()
        self.last_html: str | None = None
        self._shown_html: str | None = None
        self._shown_notice: tuple[str, str] | None = None

    # --------------------------------------------------------------- öffentlich
    def reload(self) -> None:
        """Datei neu lesen und anzeigen. Wirft nie."""
        with self._lock:
            try:
                html, notice = self._build()
            except Exception as exc:  # letzte Absicherung
                log.exception("Unerwarteter Fehler")
                html, notice = None, ("error", t("render.unexpected", error=exc))
            self._emit(html, notice)

    # --------------------------------------------------------------- intern
    def _fallback(self, message: str) -> str | None:
        """Ohne bisherigen Stand eine Meldung als Inhalt zeigen, sonst nichts ändern."""
        return None if self.last_html is not None else _message_html(message)

    def _build(self) -> tuple[str | None, tuple[str, str] | None]:
        if not self.path.is_file():
            if self.last_html is None:
                msg = t("file.not_found_body", path=self.path)
                return _message_html(msg), ("warn", t("file.not_found"))
            return None, ("warn", t("file.missing"))
        try:
            text = read_text_file(self.path)
        except FileTooLargeError as exc:
            return self._fallback(str(exc)), ("error", str(exc))
        except OSError as exc:
            msg = t("file.unreadable", error=exc.strerror or exc)
            return self._fallback(msg), ("error", msg)
        try:
            html = self._render(text, self.fmt, self.path.parent, self._inliner)
        except PandocNotFoundError as exc:
            return self._fallback(str(exc)), ("error", str(exc).split("\n", 1)[0])
        except PandocError as exc:
            msg = t("render.mediawiki_failed", error=exc)
            return self._fallback(msg), ("error", msg)
        except RecursionError:
            msg = t("render.too_deep")
            return self._fallback(msg), ("error", msg)
        except Exception as exc:
            msg = t("render.error", kind=type(exc).__name__, error=str(exc)[:300])
            log.debug("Renderfehler", exc_info=True)
            return self._fallback(msg), ("error", msg + t("render.keeping_last"))
        self.last_html = html
        return html, None

    def _emit(self, html: str | None, notice: tuple[str, str] | None) -> None:
        payload: Payload = {}
        if html is not None and html != self._shown_html:
            payload["html"] = html
            self._shown_html = html
        if notice != self._shown_notice:
            payload["notice"] = notice[1] if notice else None
            payload["level"] = notice[0] if notice else None
            self._shown_notice = notice
        if not payload:
            return  # nichts geändert → DOM nicht anfassen (Scrollposition bleibt ruhig)
        try:
            self._push(payload)
        except Exception:
            log.exception("Anzeige konnte nicht aktualisiert werden")
