"""Dateiüberwachung mit echtem watchdog (kein Display nötig)."""

import os
import threading
import time

import pytest

from kimbaview.controller import DocumentController
from kimbaview.watcher import FileWatcher

TIMEOUT = 5.0


class Recorder:
    def __init__(self):
        self.calls: list[bool] = []
        self.cond = threading.Condition()

    def __call__(self, exists: bool):
        with self.cond:
            self.calls.append(exists)
            self.cond.notify_all()

    def wait_for(self, predicate, timeout=TIMEOUT):
        deadline = time.monotonic() + timeout
        with self.cond:
            while not predicate(self.calls):
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self.cond.wait(left)
            return True

    def settle(self, quiet=0.6):
        """Warten, bis eine Zeit lang keine Ereignisse mehr kommen."""
        n = -1
        while n != len(self.calls):
            n = len(self.calls)
            time.sleep(quiet)


@pytest.fixture
def watched(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# eins", encoding="utf-8")
    rec = Recorder()
    w = FileWatcher(f, rec, debounce=0.2)
    w.start()
    time.sleep(0.3)  # Observer betriebsbereit
    yield f, rec
    w.stop()


def test_change_detected(watched):
    f, rec = watched
    f.write_text("# zwei", encoding="utf-8")
    assert rec.wait_for(lambda c: c and c[-1] is True)


def test_atomic_save_detected(watched):
    f, rec = watched
    tmp = f.with_name(".doc.md.tmp~")
    tmp.write_text("# atomar", encoding="utf-8")
    os.replace(tmp, f)
    assert rec.wait_for(lambda c: c and c[-1] is True)
    assert f.read_text(encoding="utf-8") == "# atomar"


def test_delete_and_restore(watched):
    f, rec = watched
    f.unlink()
    assert rec.wait_for(lambda c: False in c)
    rec.settle()
    n = len(rec.calls)
    f.write_text("# wieder da", encoding="utf-8")
    assert rec.wait_for(lambda c: len(c) > n and c[-1] is True)


def test_rename_away_and_back(watched):
    f, rec = watched
    other = f.with_name("umbenannt.md")
    os.replace(f, other)
    assert rec.wait_for(lambda c: False in c)
    rec.settle()
    n = len(rec.calls)
    os.replace(other, f)
    assert rec.wait_for(lambda c: len(c) > n and c[-1] is True)


def test_other_files_ignored(watched):
    f, rec = watched
    (f.parent / "anderes.md").write_text("x", encoding="utf-8")
    time.sleep(0.8)
    assert rec.calls == []


def test_debounce_coalesces_bursts(watched):
    f, rec = watched
    for i in range(10):
        f.write_text(f"# {i}", encoding="utf-8")
        time.sleep(0.02)
    assert rec.wait_for(lambda c: len(c) >= 1)
    rec.settle()
    assert len(rec.calls) <= 2  # 10 Schreibvorgänge → (fast) ein Update


def test_two_watchers_independent(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("a"), b.write_text("b")
    ra, rb = Recorder(), Recorder()
    wa, wb = FileWatcher(a, ra), FileWatcher(b, rb)
    wa.start(), wb.start()
    try:
        time.sleep(0.3)
        a.write_text("a2")
        assert ra.wait_for(lambda c: len(c) >= 1)
        time.sleep(0.5)
        assert rb.calls == []
    finally:
        wa.stop(), wb.stop()


# ------------------------------------------------------------- Ende-zu-Ende ohne Fenster
def test_controller_with_watcher_end_to_end(tmp_path):
    f = tmp_path / "live.md"
    f.write_text("# Version 1", encoding="utf-8")
    pushed: list[dict] = []
    cond = threading.Condition()

    def push(p):
        with cond:
            pushed.append(p)
            cond.notify_all()

    ctl = DocumentController(f, "md", push)
    ctl.reload()
    w = FileWatcher(f, lambda _e: ctl.reload())
    w.start()
    time.sleep(0.3)

    def wait(pred):
        with cond:
            return cond.wait_for(lambda: pred(pushed), timeout=TIMEOUT)

    try:
        assert "Version 1" in pushed[0]["html"]
        f.write_text("# Version 2", encoding="utf-8")
        assert wait(lambda p: any("Version 2" in x.get("html", "") for x in p))
        f.unlink()
        assert wait(lambda p: p[-1].get("level") == "warn")
        assert "html" not in pushed[-1]  # letzter Stand bleibt stehen
        f.write_text("# Version 3", encoding="utf-8")
        assert wait(lambda p: "Version 3" in p[-1].get("html", ""))
        assert pushed[-1].get("notice", "x") is None  # Hinweis wieder weg
    finally:
        w.stop()
