"""Fehlerverhalten: Hinweis oben, letzter funktionierender Stand bleibt, nie abstürzen."""

from kimbaview import render_mediawiki
from kimbaview.controller import DocumentController
from kimbaview.loader import MAX_FILE_SIZE


def make(tmp_path, text="# ok", fmt="md", renderer=None, name="d.md"):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    pushed = []
    kwargs = {"renderer": renderer} if renderer else {}
    return f, pushed, DocumentController(f, fmt, pushed.append, **kwargs)


def test_render_error_keeps_last_good(tmp_path):
    state = {"fail": False}
    from kimbaview.render import render_document

    def renderer(*a):
        if state["fail"]:
            raise ValueError("halbfertige Syntax")
        return render_document(*a)

    f, pushed, ctl = make(tmp_path, renderer=renderer)
    ctl.reload()
    good = pushed[-1]["html"]
    state["fail"] = True
    f.write_text("# kaputt", encoding="utf-8")
    ctl.reload()
    assert "html" not in pushed[-1]
    assert pushed[-1]["level"] == "error" and "halbfertige Syntax" in pushed[-1]["notice"]
    assert ctl.last_html == good
    state["fail"] = False
    ctl.reload()
    assert pushed[-1]["notice"] is None


def test_unexpected_exceptions_never_escape(tmp_path):
    def boom(*a):
        raise MemoryError("x")

    _, pushed, ctl = make(tmp_path, renderer=boom)
    ctl.reload()  # darf nicht werfen
    assert pushed[-1]["level"] == "error"


def test_push_failure_does_not_crash(tmp_path):
    f = tmp_path / "d.md"
    f.write_text("# x")

    def bad_push(_):
        raise RuntimeError("Fenster weg")

    DocumentController(f, "md", bad_push).reload()


def test_recursion_error(tmp_path):
    def deep(*a):
        raise RecursionError

    _, pushed, ctl = make(tmp_path, renderer=deep)
    ctl.reload()
    assert "verschachtelt" in pushed[-1]["notice"]


def test_too_large_file(tmp_path):
    f, pushed, ctl = make(tmp_path)
    with open(f, "wb") as fh:
        fh.truncate(MAX_FILE_SIZE + 10)
    ctl.reload()
    assert pushed[-1]["level"] == "error" and "zu groß" in pushed[-1]["notice"]


def test_missing_at_start_then_appears(tmp_path):
    f = tmp_path / "spaeter.md"
    pushed = []
    ctl = DocumentController(f, "md", pushed.append)
    ctl.reload()
    assert "nicht gefunden" in pushed[-1]["html"]
    f.write_text("# da", encoding="utf-8")
    ctl.reload()
    assert ">da</h1>" in pushed[-1]["html"] and pushed[-1]["notice"] is None


def test_unchanged_content_not_pushed_again(tmp_path):
    _, pushed, ctl = make(tmp_path)
    ctl.reload()
    ctl.reload()
    assert len(pushed) == 1


def test_pandoc_missing_shows_hint_markdown_still_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(render_mediawiki, "find_pandoc", lambda: None)
    _, pushed, ctl = make(tmp_path, "= T =", "mediawiki", name="w.wiki")
    ctl.reload()
    assert "Pandoc" in pushed[-1]["html"] and "Installation" in pushed[-1]["html"]
    assert pushed[-1]["level"] == "error"
    _, pushed2, ctl2 = make(tmp_path, "# T", "md")
    ctl2.reload()
    assert "<h1" in pushed2[-1]["html"]


def test_notice_text_is_not_html(tmp_path):
    # Hinweise werden im Fenster per textContent gesetzt; im HTML-Fallback escaped.
    f = tmp_path / "<b>x</b>.md"
    pushed = []
    DocumentController(f, "md", pushed.append).reload()
    assert "<b>x</b>" not in pushed[-1]["html"]
