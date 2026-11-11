"""Links zwischen lokalen Dokumenten – Auflösung und Sicherheit (ohne Display)."""

import os
import sys
from pathlib import Path

import pytest

from kimbaview.images import ImageInliner
from kimbaview.navigation import LinkError, NavRequest, parse_nav_request, resolve_doc_link
from kimbaview.render import render_document


@pytest.fixture
def site(tmp_path):
    root = tmp_path / "wiki"
    (root / "sub" / "tief").mkdir(parents=True)
    (root / "index.md").write_text("# Index")
    (root / "zweite.markdown").write_text("# 2")
    (root / "Haupt Seite.wiki").write_text("= H =")
    (root / "sub" / "a.md").write_text("# A")
    (root / "sub" / "tief" / "b.mediawiki").write_text("= B =")
    (root / "sub" / "Datei mit Leerzeichen.md").write_text("# L")
    (root / "notiz.txt").write_text("x")
    (root / "programm.exe").write_bytes(b"MZ")
    (root / "bild.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "geheim.md").write_text("# außerhalb")
    return root


def link(site, current, href, fmt="md"):
    return resolve_doc_link(site / current, href, site.resolve(), fmt)


# ------------------------------------------------------------------ erlaubt
@pytest.mark.parametrize(
    "current, href, expected",
    [
        ("index.md", "sub/a.md", "sub/a.md"),
        ("index.md", "./zweite.markdown", "zweite.markdown"),
        ("index.md", "sub/tief/b.mediawiki", "sub/tief/b.mediawiki"),
        ("sub/a.md", "../index.md", "index.md"),               # nach oben innerhalb der Wurzel
        ("sub/tief/b.mediawiki", "../../index.md", "index.md"),
        ("index.md", "sub/Datei%20mit%20Leerzeichen.md", "sub/Datei mit Leerzeichen.md"),
        ("index.md", "SUB/A.MD" if sys.platform == "win32" else "sub/a.md", "sub/a.md"),
    ],
)
def test_links_inside_root(site, current, href, expected):
    t = link(site, current, href)
    assert t.path == (site / expected).resolve()
    assert t.fragment is None


def test_fragment_is_returned(site):
    t = link(site, "index.md", "sub/a.md#ab-schnitt")
    assert t.path.name == "a.md" and t.fragment == "ab-schnitt"


def test_wikilink_without_extension(site):
    # Pandoc macht aus [[Haupt Seite]] den Link "Haupt_Seite"
    t = link(site, "index.md", "Haupt_Seite", fmt="mediawiki")
    assert t.path.name == "Haupt Seite.wiki"


def test_markdown_link_without_extension(site):
    assert link(site, "index.md", "sub/a").path.name == "a.md"


# ------------------------------------------------------------------ abgelehnt
@pytest.mark.parametrize(
    "href",
    [
        "../geheim.md",
        "sub/../../geheim.md",
        "%2e%2e/geheim.md",
        "..%2Fgeheim.md",
    ],
)
def test_outside_root_rejected(site, href):
    with pytest.raises(LinkError, match="außerhalb"):
        link(site, "index.md", href)


def test_outside_root_rejected_from_subfolder(site):
    with pytest.raises(LinkError):
        link(site, "sub/a.md", "../../geheim.md")


@pytest.mark.parametrize(
    "href",
    [
        "/etc/passwd.md",
        "C:/Windows/x.md",
        "file:///C:/x.md",
        "https://example.org/x.md",
        "//server/share/x.md",
        "\\\\server\\share\\x.md",
    ],
)
def test_absolute_and_remote_rejected(site, href):
    with pytest.raises(LinkError):
        link(site, "index.md", href)


@pytest.mark.parametrize("href", ["notiz.txt", "programm.exe", "bild.png", "sub/"])
def test_non_document_files_never_opened(site, href):
    with pytest.raises(LinkError):
        link(site, "index.md", href)


def test_missing_target(site):
    with pytest.raises(LinkError, match="nicht gefunden"):
        link(site, "index.md", "fehlt.md")


def test_symlinked_dir_outside_root_rejected(site, tmp_path):
    outside = tmp_path / "draussen"
    outside.mkdir()
    (outside / "x.md").write_text("# x")
    lnk = site / "verweis"
    try:
        os.symlink(outside, lnk, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            raise
        import _winapi

        _winapi.CreateJunction(str(outside), str(lnk))
    with pytest.raises(LinkError):
        link(site, "index.md", "verweis/x.md")


# ------------------------------------------------------------------ Anfragen aus dem Fenster
@pytest.mark.parametrize(
    "value, expected",
    [
        ({"action": "open", "href": "a.md", "mode": "same", "seq": 1}, NavRequest("open", "a.md", False)),
        ({"action": "open", "href": "a.md", "mode": "new"}, NavRequest("open", "a.md", True)),
        ({"action": "back", "seq": 3}, NavRequest("back")),
        ({"action": "forward"}, NavRequest("forward")),
    ],
)
def test_parse_valid_requests(value, expected):
    assert parse_nav_request(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        None, "a.md", 42, [], {},
        {"action": "exec", "href": "calc.exe"},
        {"action": "open"},
        {"action": "open", "href": ""},
        {"action": "open", "href": 5},
        {"action": "open", "href": "a" * 5000},
        {"action": "open", "href": "a.md", "mode": "popup"},
    ],
)
def test_parse_rejects_invalid(value):
    assert parse_nav_request(value) is None


# ------------------------------------------------------------------ Bilder mit Wurzel
def test_images_from_parent_inside_root(site):
    (site / "sub" / "seite.md").write_text("![x](../bild.png)")
    out = render_document("![x](../bild.png)", "md", site / "sub", ImageInliner(site / "sub", site))
    assert 'src="data:image/png;base64,' in out


def test_images_outside_root_still_blocked(site, tmp_path):
    (tmp_path / "geheim.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    out = render_document("![x](../../geheim.png)", "md", site / "sub", ImageInliner(site / "sub", site))
    assert "<img" not in out


def test_examples_are_linked(examples):
    t = resolve_doc_link(examples / "example.md", "unterordner/seite.md", examples.resolve())
    assert t.path.name == "seite.md"
    back = resolve_doc_link(t.path, "../example.md#tabelle", examples.resolve())
    assert back.path.name == "example.md" and back.fragment == "tabelle"
