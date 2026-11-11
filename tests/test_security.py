"""Sicherheitstests – laufen ohne Grafikdisplay."""

import os
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import pytest

from conftest import requires_pandoc
from kimbaview import links, render_mediawiki
from kimbaview.loader import MAX_FILE_SIZE, FileTooLargeError, read_text_file
from kimbaview.page import build_shell, content_security_policy, update_script
from kimbaview.paths import resolve_local_resource
from kimbaview.render import render_document
from kimbaview.render_mediawiki import (
    PandocNotFoundError,
    PandocTimeoutError,
    build_pandoc_command,
    run_pandoc,
)
from kimbaview.sanitize import sanitize_html


def md(text, base=Path(".")):
    return render_document(text, "md", base)


def _no_handlers(html: str) -> bool:
    return re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE) is None


# ------------------------------------------------------------------ Skripte & Handler
def test_script_tag_removed():
    out = md("Hallo\n\n<script>alert('x')</script>\n\n<script src='https://e/x.js'></script>")
    assert "<script" not in out.lower()
    assert "alert" not in out


@pytest.mark.parametrize(
    "snippet",
    [
        '<p onclick="alert(1)">x</p>',
        '<img src="a.png" onerror="alert(1)">',
        "<details open ontoggle=alert(1)><summary>s</summary></details>",
        '<a href="https://e" onmouseover="alert(1)">x</a>',
        "<div ONCLICK='alert(1)'>x</div>",
    ],
)
def test_event_handlers_removed(snippet):
    out = md(snippet)
    assert _no_handlers(out)
    assert "alert" not in out


@pytest.mark.parametrize(
    "tag",
    [
        '<iframe src="https://e"></iframe>',
        '<object data="x.swf"></object>',
        '<embed src="x.swf">',
        '<form action="https://e"><input name="pw"></form>',
        "<style>body{background:url(https://e/t)}</style>",
        '<link rel="stylesheet" href="https://e/x.css">',
        '<meta http-equiv="refresh" content="0;url=https://e">',
        '<base href="https://e/">',
        "<svg onload=alert(1)><circle/></svg>",
        "<math><mtext><script>alert(1)</script></mtext></math>",
    ],
)
def test_dangerous_tags_removed(tag):
    out = md(tag).lower()
    for bad in ("<iframe", "<object", "<embed", "<form", "<style", "<link", "<meta", "<base", "<svg", "<script", "<input"):
        assert bad not in out
    assert "url(" not in out
    assert "alert" not in out


def test_style_attribute_removed():
    out = md('<div style="position:fixed;inset:0">x</div><p style="color:red">y</p>')
    assert "style=" not in out


# ------------------------------------------------------------------ Links
@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "JaVaScRiPt:alert(1)",
        " javascript:alert(1)",
        "jav&#x09;ascript:alert(1)",
        "&#106;avascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "//evil.example/x",
    ],
)
def test_bad_link_schemes_removed(href):
    out_html = md(f'<a href="{href}">x</a>')
    out_md = md(f"[x]({href})")
    for out in (out_html, out_md):
        hrefs = re.findall(r'href="([^"]*)"', out)
        assert all(h.startswith(("http://", "https://", "#")) for h in hrefs), hrefs
        # markdown-it lässt ungültige Links als reinen Text stehen – das ist harmlos,
        # aber es darf nirgends ein Attribut damit entstehen:
        assert not re.search(r'="[^"]*(javascript|vbscript|data:|file:)', out, re.IGNORECASE)


def test_http_links_kept():
    out = md("[a](https://example.org) [b](http://example.org)")
    assert 'href="https://example.org"' in out and 'href="http://example.org"' in out


def test_ids_are_prefixed_against_dom_clobbering():
    out = md('<a id="__kimbaview">x</a> <div id="wv-content">y</div> [s](#wv-content)')
    assert 'id="__kimbaview"' not in out and 'id="wv-content"' not in out
    assert 'id="wv-u-__kimbaview"' in out
    assert 'href="#wv-u-wv-content"' in out
    assert "name=" not in out


def test_only_checkbox_inputs_survive():
    out = md('<input type="text" value="x"><input type="password">\n\n- [x] ok')
    assert out.count("<input") == 1 and 'type="checkbox"' in out


def test_classes_are_allowlisted():
    out = md('<span class="wv-notice evil">x</span><pre class="anything">y</pre>')
    assert "wv-notice" not in out and "evil" not in out and "anything" not in out


@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://example.org", True),
        ("http://example.org/a?b#c", True),
        ("javascript:alert(1)", False),
        ("file:///C:/Windows/win.ini", False),
        ("data:text/html,x", False),
        ("ms-settings:", False),
        ("about:blank", False),
        ("https://", False),
        ("https://exa mple.org", False),
        ("https://example.org/\x00", False),
        ("", False),
        (None, False),
    ],
)
def test_is_safe_external_url(url, ok):
    assert links.is_safe_external_url(url) is ok


def test_browser_guard_blocks_other_schemes(monkeypatch):
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url, new=0, autoraise=True: opened.append(url) or True)
    monkeypatch.setattr(links, "_installed", False)
    links.install_browser_guard()
    assert webbrowser.open("file:///C:/Windows/System32/calc.exe") is False
    assert webbrowser.open("javascript:alert(1)") is False
    assert webbrowser.open_new_tab("ms-msdt:/id x") is False
    assert webbrowser.open("https://example.org") is True
    assert opened == ["https://example.org"]


# ------------------------------------------------------------------ Bilder & Pfade
def test_external_images_not_loaded():
    out = md("![p](https://evil.example/p.gif) <img src='http://evil.example/b.png'>")
    assert "<img" not in out
    assert "Externes Bild nicht geladen" in out
    assert "https://evil.example/p.gif" in out  # Adresse wird angezeigt


def test_data_image_from_document_dropped():
    out = md('<img src="data:image/svg+xml;base64,PHN2Zz4=">')
    assert "data:" not in out


@pytest.fixture
def tree(tmp_path):
    base = tmp_path / "doc"
    (base / "sub").mkdir(parents=True)
    (base / "sub" / "ok.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (base / "ok.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (tmp_path / "secret.png").write_bytes(b"\x89PNG\r\n\x1a\nsecret")
    return base


def test_resolve_inside(tree):
    assert resolve_local_resource(tree, "ok.png") is not None
    assert resolve_local_resource(tree, "sub/ok.png") is not None
    assert resolve_local_resource(tree, "sub/../ok.png") is not None
    assert resolve_local_resource(tree, "./sub/ok.png?x=1#y") is not None


@pytest.mark.parametrize(
    "ref",
    [
        "../secret.png",
        "sub/../../secret.png",
        "%2e%2e/secret.png",
        "..%2fsecret.png",
        "..\\secret.png",
        "/etc/passwd",
        "\\\\server\\share\\x.png",
        "//server/share/x.png",
        "C:/Windows/win.ini",
        "C:\\Windows\\win.ini",
        "file:///etc/passwd",
        "ok.png:stream" if sys.platform == "win32" else "nonexistent.png",
        "nonexistent.png",
        "sub",
        "ok.png\x00.txt",
        "",
    ],
)
def test_resolve_rejects_outside(tree, ref):
    assert resolve_local_resource(tree, ref) is None


def test_traversal_image_rendered_as_placeholder(tree):
    out = md("![x](../secret.png)", tree)
    assert "<img" not in out and "außerhalb" in out


def _make_dir_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        if sys.platform != "win32":
            raise
    import _winapi  # Junctions brauchen unter Windows keine Adminrechte

    _winapi.CreateJunction(str(target), str(link))


def test_symlink_file_outside_rejected(tree):
    link = tree / "link.png"
    try:
        os.symlink(tree.parent / "secret.png", link)
    except (OSError, NotImplementedError):
        pytest.skip("Datei-Symlinks hier nicht erlaubt (Windows ohne Entwicklermodus)")
    assert resolve_local_resource(tree, "link.png") is None
    assert "<img" not in md("![x](link.png)", tree)


def test_directory_link_outside_rejected(tree, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    _make_dir_link(tree / "linkdir", outside)
    assert (tree / "linkdir" / "x.png").exists()
    assert resolve_local_resource(tree, "linkdir/x.png") is None


def test_symlink_inside_allowed(tree):
    try:
        _make_dir_link(tree / "alias", tree / "sub")
    except OSError:
        pytest.skip("Links nicht möglich")
    assert resolve_local_resource(tree, "alias/ok.png") is not None


# ------------------------------------------------------------------ Dateien
def test_too_large_file_rejected(tmp_path):
    f = tmp_path / "big.md"
    with open(f, "wb") as fh:
        fh.truncate(MAX_FILE_SIZE + 1)
    with pytest.raises(FileTooLargeError):
        read_text_file(f)


def test_file_at_limit_ok(tmp_path):
    f = tmp_path / "ok.md"
    f.write_bytes(b"#" * 10)
    assert read_text_file(f, max_size=10) == "#" * 10
    with pytest.raises(FileTooLargeError):
        read_text_file(f, max_size=9)


def test_invalid_utf8_tolerated(tmp_path):
    f = tmp_path / "bad.md"
    f.write_bytes(b"\xef\xbb\xbf# Titel \xff\xfe kaputt \xc3")
    text = read_text_file(f)
    assert text.startswith("# Titel ")
    assert "\ufffd" in text
    assert "<h1" in md(text)


# ------------------------------------------------------------------ Pandoc
def test_pandoc_command_is_minimal():
    cmd = build_pandoc_command("pandoc", (3, 13))
    assert cmd[0] == "pandoc"
    assert "--sandbox" in cmd
    assert "--from=mediawiki" in cmd and "--to=html5" in cmd
    joined = " ".join(cmd)
    for bad in ("--filter", "--lua-filter", "-L", "-F", "--standalone", "-s ", "--template",
                "--include", "--embed-resources", "--self-contained", "--extract-media",
                "--data-dir", "--defaults", "--resource-path"):
        assert bad not in joined.split() and bad not in joined
    assert "--no-highlight" in build_pandoc_command("pandoc", (3, 1))
    assert "--sandbox" not in build_pandoc_command("pandoc", (2, 9))


def test_pandoc_called_without_shell(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["kwargs"] = cmd, kwargs
        return subprocess.CompletedProcess(cmd, 0, b"<p>ok</p>", b"")

    monkeypatch.setattr(render_mediawiki, "pandoc_version", lambda p: (3, 13))
    monkeypatch.setattr(render_mediawiki.subprocess, "run", fake_run)
    assert run_pandoc("x", pandoc="pandoc") == "<p>ok</p>"
    assert isinstance(seen["cmd"], list)
    assert seen["kwargs"]["shell"] is False
    assert seen["kwargs"]["timeout"] == 10.0
    assert seen["kwargs"]["input"] == b"x"


def test_pandoc_timeout(monkeypatch, tmp_path):
    slow = [sys.executable, "-c", "import time; time.sleep(30)"]
    monkeypatch.setattr(render_mediawiki, "pandoc_version", lambda p: (3, 13))
    monkeypatch.setattr(render_mediawiki, "build_pandoc_command", lambda p, v: slow)
    t0 = time.monotonic()
    with pytest.raises(PandocTimeoutError):
        run_pandoc("= x =", pandoc="fake", timeout=1.0)
    assert time.monotonic() - t0 < 10


def test_pandoc_missing_gives_hint(monkeypatch):
    monkeypatch.setattr(render_mediawiki, "find_pandoc", lambda: None)
    with pytest.raises(PandocNotFoundError) as exc:
        render_document("= x =", "mediawiki", Path("."))
    assert "Pandoc" in str(exc.value) and "Installation" in str(exc.value)
    # Markdown funktioniert trotzdem
    assert "<h1" in render_document("# x", "md", Path("."))


@pytest.mark.parametrize("plat, word", [("win32", "winget"), ("darwin", "brew"), ("linux", "apt")])
def test_install_hint_per_os(plat, word):
    assert word in render_mediawiki.pandoc_install_hint(plat)


@requires_pandoc
def test_mediawiki_output_sanitized():
    src = (
        '<span onclick="alert(1)">a</span><script>alert(2)</script>'
        '<div style="position:fixed">b</div>[javascript:alert(3) x]'
        '<iframe src="https://e"></iframe>'
    )
    out = render_document(src, "mediawiki", Path("."))
    assert _no_handlers(out) and "<script" not in out and "style=" not in out
    assert "<iframe" not in out and 'href="javascript' not in out


# ------------------------------------------------------------------ Seite / CSP
def test_csp_is_strict():
    csp = content_security_policy("N0NCE")
    assert "default-src 'none'" in csp
    assert "script-src 'nonce-N0NCE'" in csp
    assert "style-src 'nonce-N0NCE'" in csp
    assert "img-src data:" in csp
    assert "connect-src 'none'" in csp and "font-src 'none'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "http" not in csp and "*" not in csp


def test_shell_has_no_external_resources_and_uses_nonce():
    shell = build_shell("<Titel>", "abc123")
    assert 'http-equiv="Content-Security-Policy"' in shell
    assert '<script nonce="abc123">' in shell and '<style nonce="abc123">' in shell
    assert shell.count("<script") == 1
    assert "&lt;Titel&gt;" in shell
    assert not re.search(r'(src|href)\s*=\s*"(https?:)?//', shell)
    assert "@import" not in shell and "url(" not in shell


def test_update_script_is_json_literal():
    js = update_script({"html": "</script><script>alert(1)</script>\u2028"})
    assert "\u2028" not in js
    assert js.startswith("window.__kimbaview && window.__kimbaview.update({")


# ------------------------------------------------------------------ evil.md
def test_evil_md_is_harmless(examples):
    out = render_document((examples / "evil.md").read_text("utf-8"), "md", examples)
    low = out.lower()
    assert "<script" not in low and "<iframe" not in low and "<object" not in low
    assert "<embed" not in low and "<form" not in low and "<style" not in low
    assert "<svg" not in low and "<meta" not in low and "<base" not in low and "<link" not in low
    assert _no_handlers(out)
    assert "style=" not in low
    assert not re.search(r'href="(?!https?://|#|[\w.-]+\.md")', out)
    assert not re.search(r'src="(?!data:image/)', out)
    assert "https://evil.example/pixel.gif" in out  # als Text-Platzhalter


def test_sanitizer_idempotent_on_evil(examples):
    out = render_document((examples / "evil.md").read_text("utf-8"), "md", examples)
    # Ein zweiter Durchlauf darf nichts Gefährliches „freilegen“.
    again = sanitize_html(out)
    assert "<script" not in again and _no_handlers(again)
