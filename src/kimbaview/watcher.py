"""Dateiüberwachung mit watchdog.

Überwacht wird das *Verzeichnis* der Datei (nicht rekursiv), weil viele
Editoren atomar speichern: Sie schreiben eine temporäre Datei und benennen
sie anschließend um. Eine Überwachung nur der Datei würde das verpassen.
Ereignisse werden entprellt (Standard 200 ms); danach wird der Callback
mit ``exists`` (bool) aufgerufen – aber nur, wenn sich der Dateistand
(vorhanden + Inhalt) seit dem letzten Aufruf tatsächlich geändert hat.
Das filtert Phantom-Ereignisse heraus, z. B. verspätet zugestellte
FSEvents unter macOS für Schreibvorgänge vor dem Start der Überwachung.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 0.2
OBSERVER_TIMEOUT = 0.1


_State = tuple[bool, bytes | None]


def _file_state(path: Path) -> _State:
    """(existiert, Inhalts-Hash). Hash ``None``, wenn die Datei nicht lesbar ist."""
    if not path.is_file():
        return (False, None)
    try:
        return (True, hashlib.blake2b(path.read_bytes(), digest_size=16).digest())
    except OSError:
        return (True, None)


def _key(path: str | os.PathLike[str] | bytes) -> str:
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    return os.path.normcase(os.path.abspath(os.fspath(path)))


class FileWatcher:
    def __init__(
        self,
        path: str | Path,
        callback: Callable[[bool], None],
        debounce: float = DEBOUNCE_SECONDS,
    ) -> None:
        self.path = Path(os.path.abspath(path))
        self._key = _key(self.path)
        self._callback = callback
        self._debounce = debounce
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._observer: Observer | None = None
        self._stopped = False
        self._state: _State | None = None

    # ---------------------------------------------------------------- Lebenszyklus
    def start(self) -> None:
        self._state = _file_state(self.path)
        handler = _Handler(self)
        # watchdog sammelt Ereignisse, bis `timeout` Sekunden Ruhe herrscht (Standard 1 s,
        # unter Windows deutlich spürbar). Unsere eigene Entprellung übernimmt das Bündeln.
        observer = Observer(timeout=OBSERVER_TIMEOUT)
        observer.daemon = True
        observer.schedule(handler, str(self.path.parent), recursive=False)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
            except Exception:  # pragma: no cover - beim Beenden egal
                log.debug("Observer konnte nicht sauber beendet werden", exc_info=True)
            self._observer = None

    # ---------------------------------------------------------------- Ereignisse
    def _relevant(self, event: FileSystemEvent) -> bool:
        paths = [event.src_path, getattr(event, "dest_path", None)]
        for p in paths:
            if p and _key(p) == self._key:
                return True
        # Wird der überwachte Ordner selbst entfernt, ist die Datei ebenfalls weg.
        if event.is_directory and event.event_type in ("deleted", "moved"):
            if _key(event.src_path) == _key(self.path.parent):
                return True
        return False

    def _schedule(self) -> None:
        with self._lock:
            if self._stopped:
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._timer = None
        state = _file_state(self.path)
        exists, digest = state
        # Unverändert → nichts melden. Vorhanden, aber unlesbar (z. B. unter Windows
        # gerade gesperrt) → sicherheitshalber trotzdem melden.
        if state == self._state and (digest is not None or not exists):
            return
        self._state = state
        try:
            self._callback(exists)
        except Exception:
            log.exception("Fehler im Datei-Callback")


class _Handler(FileSystemEventHandler):
    def __init__(self, watcher: FileWatcher) -> None:
        self._w = watcher

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("opened", "closed_no_write"):
            return
        if self._w._relevant(event):
            self._w._schedule()
