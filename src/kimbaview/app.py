"""Kommandozeile und Fenster (pywebview).

Aufbau pro Fenster:  FileWatcher → DocumentController → push() → run_js(update)

* Kein lokaler Server, kein Netzwerkport: die Hülle wird per ``html=``
  geladen, Inhalte werden per ``run_js`` eingeschoben.
* Keine JS-API-Brücke (``js_api``) – JavaScript kann keine Python-Funktion
  aufrufen. Externe Links laufen über pywebviews Standard-Behandlung für
  neue Fenster, die in ``links.install_browser_guard`` abgesichert ist.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
from importlib.resources import files
from pathlib import Path

from kimbaview import __version__
from kimbaview.controller import DocumentController
from kimbaview.formats import FORMATS, MARKDOWN, UnknownFormatError, detect_format
from kimbaview.i18n import LANGUAGES, set_language, t
from kimbaview.navigation import LinkError, parse_nav_request, resolve_doc_link
from kimbaview.page import build_shell, new_nonce, update_script
from kimbaview.settings import DEFAULT_WIDTH, load_settings, save_settings, valid_width

log = logging.getLogger("kimbaview")

def _file_types() -> tuple[str, str]:
    return (t("dialog.filter_docs"), t("dialog.filter_all"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    # Sprache schon vor dem Parsen setzen (für die Hilfetexte); --lang wird in main() angewendet.
    lang = None
    args_list = list(sys.argv[1:] if argv is None else argv)
    for i, a in enumerate(args_list):
        if a.startswith("--lang="):
            lang = a.split("=", 1)[1]
        elif a == "--lang" and i + 1 < len(args_list):
            lang = args_list[i + 1]
    set_language(lang)
    p = argparse.ArgumentParser(prog="kimbaview", description=t("cli.description"))
    p.add_argument("files", nargs="*", metavar=t("cli.files_meta"), help=t("cli.files"))
    p.add_argument("--format", choices=FORMATS, default=None, help=t("cli.format"))
    p.add_argument("--lang", choices=LANGUAGES, default=None, help=t("cli.lang"))
    p.add_argument("--debug", action="store_true", help=t("cli.debug"))
    p.add_argument("--version", action="version", version=f"kimbaview {__version__}")
    # Für die Build-Pipeline: prüft das gebaute Paket ohne Fenster (Exit-Code 0 = ok)
    p.add_argument("--selftest", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def selftest() -> int:
    """Rendert Testinhalte und importiert die GUI-Bibliothek – ohne Fenster.

    Findet fehlende Module/Daten in PyInstaller-/py2app-Builds (z. B. Pygments-
    Lexer, nh3, Assets). Ausgabe nur, wenn eine Konsole vorhanden ist.
    """
    checks: list[tuple[str, bool]] = []
    try:
        from kimbaview.page import build_shell
        from kimbaview.render import render_document
        from kimbaview.render_mediawiki import find_pandoc

        md = (
            "# T\n\n| a | b |\n|---|--:|\n| 1 | 2 |\n\n```python\ndef f(): pass\n```\n\n"
            "<script>alert(1)</script>\n\n[x](javascript:alert(1)) [y](https://example.org)\n"
        )
        out = render_document(md, "md", Path("."))
        checks.append(("markdown", "<table>" in out and "<h1" in out))
        checks.append(("pygments", '<span class="k">def</span>' in out))
        checks.append(("sanitizer", "<script" not in out and 'href="javascript' not in out
                       and 'href="https://example.org"' in out))
        checks.append(("assets", "Content-Security-Policy" in build_shell("t", "n")))
        if find_pandoc():
            wiki = render_document("= W =\n{{Vorlage}}", "mediawiki", Path("."))
            checks.append(("pandoc", "wv-template" in wiki))
        import webview  # noqa: F401  – GUI-Bibliothek gebündelt?

        checks.append(("pywebview", True))
    except Exception as exc:  # pragma: no cover - nur im Fehlerfall
        checks.append((f"Fehler: {type(exc).__name__}: {exc}", False))
    ok = all(c[1] for c in checks)
    if sys.stdout is not None:
        for name, passed in checks:
            print(f"{'OK  ' if passed else 'FAIL'} {name}")
        print("kimbaview selftest " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


APP_TITLE = "kimbaview by revlat"


def window_title(path: Path | None) -> str:
    return f"{path.name} – {APP_TITLE}" if path else APP_TITLE


def resolve_format(path: str | Path, override: str | None) -> str:
    """Wie detect_format, aber unbekannte Endungen werden als Markdown angezeigt."""
    try:
        return detect_format(path, override)
    except UnknownFormatError:
        if override is not None:
            raise
        log.info("Unbekannte Endung bei %s – wird als Markdown angezeigt", path)
        return MARKDOWN


def _system_prefers_dark() -> bool:
    """Nur für die Fenster-Hintergrundfarbe vor dem ersten Rendern (kein Aufblitzen)."""
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        pass
    return False


def _icon_path() -> str | None:
    """Fenster-Icon (Windows: .ico, sonst .png). In der gebauten .exe nutzt
    Windows ohnehin das eingebettete Programm-Icon."""
    try:
        name = "kimbaview.ico" if sys.platform == "win32" else "kimbaview.png"
        path = Path(str(files("kimbaview").joinpath("assets", name)))
        return str(path) if path.is_file() else None
    except Exception:
        return None


class ViewerWindow:
    """Ein Fenster mit eigenem Watcher, Zustand und Verlauf.

    Links auf andere lokale Dokumente werden im selben Fenster geöffnet
    (mit Zurück/Vor) oder per Strg-/Mittelklick in einem neuen Fenster. Die
    Anfrage kommt über ``pywebview.state["wv_nav"]`` – es gibt weiterhin keine
    JS-API-Funktion. Jede Anfrage wird in navigation.py streng geprüft.
    """

    def __init__(
        self,
        webview_mod,
        path: Path | None,
        fmt_override: str | None,
        text_width: int = DEFAULT_WIDTH,
        root: Path | None = None,
        fragment: str | None = None,
    ) -> None:
        self._webview = webview_mod
        self._fmt_override = fmt_override
        self._text_width = text_width
        self._nonce = new_nonce()
        self._ready = threading.Event()
        self._closed = threading.Event()
        self._started = False
        self._lock = threading.RLock()
        self._gen = 0
        self._history: list[dict] = []  # {"path": Path, "scroll": float}
        self._hpos = -1
        self._initial_fragment = fragment
        self.root = root
        self.fmt = MARKDOWN
        self.controller: DocumentController | None = None
        self.watcher = None
        self.path = path
        title = window_title(path)
        self.window = webview_mod.create_window(
            title,
            html=build_shell(title, self._nonce, text_width),
            width=1000,
            height=900,
            min_size=(360, 300),
            text_select=True,
            zoomable=True,
            background_color="#0D1117" if _system_prefers_dark() else "#FFFFFF",
        )
        self.window.events.loaded += self._on_loaded
        self.window.events.closed += self._on_closed
        state = self.window.state
        state += self._on_state  # Handler läuft in eigenem Thread

    # ------------------------------------------------------------ Ereignisse
    def _on_loaded(self) -> None:
        if self._started:  # nur die erste Ladung zählt
            return
        self._started = True
        self._ready.set()
        if self.path is None:
            self._ask_for_file()
        else:
            self._attach(self.path)

    def _on_closed(self) -> None:
        # Bewusst ohne self._lock: Eine laufende Navigation könnte gerade auf den
        # GUI-Thread warten (evaluate_js) – das würde sonst verklemmen.
        self._closed.set()
        self._gen += 1
        watcher = self.watcher
        if watcher is not None:
            watcher.stop()
        width = self._current_width(saved_only=True)
        if width is not None:
            save_settings({"width": width})

    def _current_width(self, saved_only: bool = False) -> int | None:
        """Vom Fenster-Skript gemeldete Textbreite (pywebview.state, keine JS-API)."""
        try:
            width = valid_width(self.window.state.get("wv_width"))
        except Exception:
            width = None
        if width is None and not saved_only:
            return self._text_width
        return width

    def _on_state(self, event_type, key, value) -> None:
        if key != "wv_nav" or str(event_type) != "change" or self._closed.is_set():
            return
        req = parse_nav_request(value)
        if req is None:
            return
        try:
            with self._lock:
                if req.action == "back":
                    self._go(-1)
                elif req.action == "forward":
                    self._go(1)
                else:
                    self._open_link(req)
        except Exception:
            log.exception("Navigation fehlgeschlagen")

    # ------------------------------------------------------------ Logik
    def _ask_for_file(self) -> None:
        try:
            result = self.window.create_file_dialog(
                self._webview.FileDialog.OPEN, allow_multiple=False, file_types=_file_types()
            )
        except Exception:
            log.exception("Dateidialog fehlgeschlagen")
            result = None
        if not result:
            self.window.destroy()
            return
        path = Path(result[0] if isinstance(result, (list, tuple)) else result)
        self.window.set_title(window_title(path))
        self._attach(path)

    def _attach(self, path: Path) -> None:
        path = Path(os.path.abspath(path))
        try:
            fmt = resolve_format(path, self._fmt_override)
        except UnknownFormatError as exc:
            self._push({"notice": str(exc), "level": "error"})
            return
        if self.root is None:
            # Wurzel = Ordner der ausdrücklich geöffneten Datei (Grenze für Links/Bilder)
            try:
                self.root = path.parent.resolve(strict=True)
            except OSError:
                self.root = path.parent
        with self._lock:
            self._history = [{"path": path, "scroll": 0.0}]
            self._hpos = 0
            self._show(path, fmt=fmt, fragment=self._initial_fragment)

    # ------------------------------------------------------------ Navigation
    def _open_link(self, req) -> None:
        if self.path is None or self.root is None:
            return
        try:
            target = resolve_doc_link(self.path, req.href, self.root, self.fmt)
        except LinkError as exc:
            self._push({"toast": str(exc)})
            return
        if req.new_window:
            ViewerWindow(
                self._webview, target.path, None, self._current_width(),
                root=self.root, fragment=target.fragment,
            )
            return
        self._remember_scroll()
        del self._history[self._hpos + 1 :]
        self._history.append({"path": target.path, "scroll": 0.0})
        self._hpos = len(self._history) - 1
        self._show(target.path, fragment=target.fragment, scroll=0.0)

    def _go(self, delta: int) -> None:
        new = self._hpos + delta
        if not 0 <= new < len(self._history):
            return
        self._remember_scroll()
        self._hpos = new
        entry = self._history[new]
        self._show(entry["path"], scroll=entry["scroll"])

    def _remember_scroll(self) -> None:
        if not 0 <= self._hpos < len(self._history):
            return
        try:
            y = self.window.evaluate_js("window.scrollY")
        except Exception:
            y = None
        if isinstance(y, (int, float)) and not isinstance(y, bool):
            self._history[self._hpos]["scroll"] = max(0.0, float(y))

    def _show(
        self,
        path: Path,
        fmt: str | None = None,
        fragment: str | None = None,
        scroll: float | None = None,
    ) -> None:
        """Dokument anzeigen; alter Watcher/Controller wird sauber abgelöst."""
        from kimbaview.watcher import FileWatcher

        self._gen += 1
        gen = self._gen
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher = None
        self.path = path
        self.fmt = fmt or resolve_format(path, None)
        self.window.set_title(window_title(path))

        def push(payload: dict, g: int = gen) -> None:
            if g == self._gen:  # Meldungen eines abgelösten Dokuments verwerfen
                self._push(payload)

        controller = DocumentController(path, self.fmt, push, root=self.root)
        self.controller = controller
        controller.reload()
        extra: dict = {"nav": {"back": self._hpos > 0, "forward": self._hpos < len(self._history) - 1}}
        if fragment:
            extra["anchor"] = fragment
        elif scroll is not None:
            extra["scroll"] = scroll
        push(extra)
        try:
            watcher = FileWatcher(path, lambda _exists, c=controller: c.reload())
            watcher.start()
            self.watcher = watcher
        except Exception as exc:
            log.exception("Überwachung konnte nicht gestartet werden")
            push({"notice": t("watch.unavailable", error=exc), "level": "warn"})

    def _push(self, payload: dict) -> None:
        if self._closed.is_set() or not self._ready.wait(timeout=30):
            return
        try:
            self.window.run_js(update_script(payload))
        except Exception:
            log.debug("Update konnte nicht ins Fenster übertragen werden", exc_info=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if args.debug:
        logging.getLogger("kimbaview").setLevel(logging.DEBUG)
    if args.selftest:
        return selftest()

    import webview  # spät importieren, damit Tests ohne GUI auskommen

    from kimbaview.links import install_browser_guard

    install_browser_guard()
    webview.settings["ALLOW_FILE_URLS"] = False
    webview.settings["ALLOW_DOWNLOADS"] = False
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    webview.settings["REMOTE_DEBUGGING_PORT"] = None

    text_width = load_settings()["width"]
    paths = [Path(f) for f in args.files] or [None]
    windows = [ViewerWindow(webview, p, args.format, text_width) for p in paths]
    webview.start(private_mode=True, debug=False, icon=_icon_path())
    del windows
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
