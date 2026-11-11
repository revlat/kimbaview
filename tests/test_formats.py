import pytest

from kimbaview.app import parse_args, resolve_format
from kimbaview.formats import MARKDOWN, MEDIAWIKI, UnknownFormatError, detect_format


@pytest.mark.parametrize(
    "name, expected",
    [
        ("a.md", MARKDOWN),
        ("a.markdown", MARKDOWN),
        ("A.MD", MARKDOWN),
        ("dir.x/readme.Markdown", MARKDOWN),
        ("a.mediawiki", MEDIAWIKI),
        ("a.wiki", MEDIAWIKI),
        ("a.wikitext", MEDIAWIKI),
        ("a.WIKI", MEDIAWIKI),
    ],
)
def test_detect_by_extension(name, expected):
    assert detect_format(name) == expected


@pytest.mark.parametrize("name", ["a.txt", "a", "a.md.bak", ".md.html"])
def test_unknown_extension(name):
    with pytest.raises(UnknownFormatError):
        detect_format(name)


def test_override_wins():
    assert detect_format("a.md", "mediawiki") == MEDIAWIKI
    assert detect_format("a.wiki", "md") == MARKDOWN
    assert detect_format("a.txt", "md") == MARKDOWN


def test_invalid_override():
    with pytest.raises(UnknownFormatError):
        detect_format("a.md", "html")


def test_cli_format_option():
    ns = parse_args(["--format", "mediawiki", "notes.txt"])
    assert ns.format == "mediawiki"
    assert ns.files == ["notes.txt"]
    assert resolve_format(ns.files[0], ns.format) == MEDIAWIKI


def test_cli_rejects_bad_format():
    with pytest.raises(SystemExit):
        parse_args(["--format", "rst", "a.md"])


def test_cli_without_file():
    assert parse_args([]).files == []


def test_window_title():
    from pathlib import Path

    from kimbaview.app import window_title

    assert window_title(Path("x/notizen.md")) == "notizen.md – kimbaview by revlat"
    assert window_title(None) == "kimbaview by revlat"


def test_selftest_passes(capsys):
    from kimbaview.app import main

    assert main(["--selftest"]) == 0
    assert "kimbaview selftest OK" in capsys.readouterr().out


def test_unknown_extension_falls_back_to_markdown_in_app():
    assert resolve_format("notes.txt", None) == MARKDOWN
