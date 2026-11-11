"""Sprachen der Oberfläche: Vollständigkeit, Auswahl, englischer Standard."""

import string
from pathlib import Path

import pytest

from kimbaview import i18n
from kimbaview.app import parse_args
from kimbaview.page import build_shell
from kimbaview.render import render_document
from kimbaview.render_mediawiki import pandoc_install_hint


def _fields(text):
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


@pytest.mark.parametrize("key", sorted(i18n.MESSAGES))
def test_every_text_exists_in_both_languages(key):
    entry = i18n.MESSAGES[key]
    assert set(entry) == set(i18n.LANGUAGES), key
    assert all(entry[lang].strip() for lang in i18n.LANGUAGES), key
    # gleiche Platzhalter in beiden Sprachen
    assert _fields(entry["en"]) == _fields(entry["de"]), key


def test_default_is_english():
    assert i18n.DEFAULT == "en"


@pytest.mark.parametrize("value, expected", [("de", "de"), ("DE", "de"), ("de_DE", "de"),
                                             ("en", "en"), ("en-US", "en"), ("fr", None), ("", None)])
def test_normalize(value, expected):
    assert i18n.normalize(value) == expected


def test_environment_variable(monkeypatch):
    monkeypatch.setenv("KIMBAVIEW_LANG", "en")
    assert i18n.set_language() == "en"
    monkeypatch.setenv("KIMBAVIEW_LANG", "de")
    assert i18n.set_language() == "de"


def test_unknown_system_language_falls_back_to_english(monkeypatch):
    monkeypatch.delenv("KIMBAVIEW_LANG", raising=False)
    monkeypatch.setattr(i18n, "_system_language", lambda: "en")
    assert i18n.set_language("fr") == "en"


def test_cli_lang_option():
    assert parse_args(["--lang", "en", "a.md"]).lang == "en"
    assert i18n.get_language() == "en"
    assert parse_args(["--lang=de"]).lang == "de"
    assert i18n.get_language() == "de"
    with pytest.raises(SystemExit):
        parse_args(["--lang", "fr"])


def test_english_texts_in_program():
    i18n.set_language("en")
    out = render_document("![x](https://example.org/a.png)", "md", Path("."))
    assert "External image not loaded" in out
    assert "Install on Windows" in pandoc_install_hint("win32")
    shell = build_shell("t", "n")
    assert '<html lang="en">' in shell and "Loading" in shell and "Ctrl+Shift" in shell
    assert '"full width"' in shell  # Text für die Breitenleiste im Skript


def test_german_texts_in_program():
    i18n.set_language("de")
    out = render_document("![x](https://example.org/a.png)", "md", Path("."))
    assert "Externes Bild nicht geladen" in out
    shell = build_shell("t", "n")
    assert '<html lang="de">' in shell and "Wird geladen" in shell and "Strg+Umschalt" in shell
    assert '"volle Breite"' in shell


def test_texts_are_escaped_in_shell(monkeypatch):
    monkeypatch.setitem(i18n.MESSAGES, "ui.back", {"en": '<b>"x"</b>', "de": '<b>"x"</b>'})
    shell = build_shell("t", "n")
    assert '<b>"x"</b>' not in shell and "&lt;b&gt;&quot;x&quot;&lt;/b&gt;" in shell
