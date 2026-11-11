"""Einstellungen (Textbreite) und Breitenleiste in der Seitenhülle."""

import json

import pytest

from kimbaview.page import build_shell
from kimbaview.settings import DEFAULT_WIDTH, WIDTH_STEPS, load_settings, save_settings, valid_width


def test_defaults_when_missing(tmp_path):
    assert load_settings(tmp_path / "nope.json") == {"width": DEFAULT_WIDTH}


def test_roundtrip(tmp_path):
    f = tmp_path / "sub" / "settings.json"
    save_settings({"width": 1200}, f)
    assert load_settings(f)["width"] == 1200
    save_settings({"width": 0}, f)  # volle Breite
    assert load_settings(f)["width"] == 0


@pytest.mark.parametrize(
    "content",
    ["{kaputt", "[]", '{"width": "1200"}', '{"width": 1234}', '{"width": -5}',
     '{"width": true}', '{"width": 1e9}', ""],
)
def test_invalid_files_fall_back(tmp_path, content):
    f = tmp_path / "settings.json"
    f.write_text(content, encoding="utf-8")
    assert load_settings(f)["width"] == DEFAULT_WIDTH


def test_oversized_file_ignored(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"width": 900, "x": "a" * 100_000}), encoding="utf-8")
    assert load_settings(f)["width"] == DEFAULT_WIDTH


@pytest.mark.parametrize("value", [None, "900", 901, True, 3.0, {"a": 1}, [900]])
def test_invalid_values_not_saved(tmp_path, value):
    f = tmp_path / "settings.json"
    save_settings({"width": value}, f)
    assert not f.exists()
    assert valid_width(value) is None


def test_valid_steps():
    assert all(valid_width(w) == w for w in WIDTH_STEPS)


def test_shell_contains_width_and_toolbar():
    shell = build_shell("t", "n0nce", 1200)
    assert 'data-wv-width="1200"' in shell
    assert 'id="wv-toolbar"' in shell and 'id="wv-full"' in shell
    assert "/*WIDTH_STEPS*/" not in shell
    assert "[600, 700, 800, 900, 1000, 1200, 1400, 0]" in shell
    assert "style=" not in shell  # nichts, was die CSP brechen würde


def test_shell_rejects_bad_width():
    assert f'data-wv-width="{DEFAULT_WIDTH}"' in build_shell("t", "n", 4711)
