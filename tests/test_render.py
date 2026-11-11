"""Rendering beider Formate (immer inklusive Sanitizer, wie im Programm)."""

from pathlib import Path

import pytest

from conftest import requires_pandoc
from kimbaview.render import render_document
from kimbaview.render_mediawiki import protect_templates, restore_templates


def md(text: str, base: Path = Path(".")) -> str:
    return render_document(text, "md", base)


def wiki(text: str, base: Path = Path(".")) -> str:
    return render_document(text, "mediawiki", base)


# ------------------------------------------------------------------ Markdown
def test_md_headings():
    out = md("# Eins\n\n## Zwei\n\n###### Sechs")
    assert '<h1 id="wv-u-eins">Eins</h1>' in out
    assert "<h2" in out and ">Zwei</h2>" in out
    assert ">Sechs</h6>" in out


def test_md_lists():
    out = md("- a\n- b\n  - c\n\n1. x\n2. y")
    assert out.count("<ul>") == 2
    assert "<ol>" in out and "<li>x</li>" in out


def test_md_table_with_alignment():
    out = md("| A | B |\n|:--|--:|\n| 1 | 2 |")
    assert "<table>" in out and "<th" in out and "<td" in out
    assert 'class="wv-align-left"' in out and 'class="wv-align-right"' in out
    assert "style=" not in out


def test_md_code_highlighted():
    out = md("```python\ndef f():\n    return 1\n```")
    assert '<pre class="wv-code"><code>' in out
    assert '<span class="k">def</span>' in out


def test_md_code_unknown_language_escaped():
    out = md("```nosuchlang\n<b>x</b>\n```")
    assert "&lt;b&gt;x&lt;/b&gt;" in out


def test_md_inline_code_and_links():
    out = md("`x<y` und [Link](https://example.org/a?b=1&c=2)")
    assert "<code>x&lt;y</code>" in out
    assert 'href="https://example.org/a?b=1&amp;c=2"' in out
    assert 'rel="noopener noreferrer"' in out


def test_md_extensions():
    out = md("~~weg~~\n\n- [x] fertig\n- [ ] offen\n\nText[^1]\n\n[^1]: Fuß")
    assert "<s>weg</s>" in out
    assert 'type="checkbox"' in out and 'disabled="disabled"' in out
    assert 'class="footnote-ref"' in out and 'href="#wv-u-fn1"' in out
    assert 'id="wv-u-fn1"' in out


def test_md_local_image_inlined(examples):
    out = md("![Bild](bilder/beispiel.png)", examples)
    assert '<img src="data:image/png;base64,' in out
    assert 'alt="Bild"' in out


# ----------------------------------------------------------------- MediaWiki
@requires_pandoc
def test_wiki_headings_lists_tables_code_links():
    src = (
        "= Eins =\n== Zwei ==\n* a\n* b\n# x\n# y\n"
        '{| class="wikitable"\n! A !! B\n|-\n| 1 || 2\n|}\n'
        '<syntaxhighlight lang="python">\ndef f(): pass\n</syntaxhighlight>\n'
        "[https://example.org Ex] [[Seite|intern]]\n"
    )
    out = wiki(src)
    assert ">Eins</h1>" in out and ">Zwei</h2>" in out
    assert "<ul>" in out and "<ol>" in out
    assert "<table>" in out and "<th>A</th>" in out and "<td>1</td>" in out
    assert '<pre class="wv-code"><code><span class="k">def</span>' in out
    assert 'href="https://example.org"' in out
    assert 'href="Seite"' in out  # interner Link: bleibt relativ, Klick wird ignoriert


@requires_pandoc
def test_wiki_templates_become_placeholders():
    out = wiki("Vor {{Infobox|a={{inner}}|b=2}} nach {{lang|de|Hallo}}.")
    assert out.count('class="wv-template"') == 2
    assert "{{Infobox}}" in out and "{{lang}}" in out
    assert "WVTPL" not in out


@requires_pandoc
def test_wiki_templates_in_nowiki_stay_text():
    out = wiki("<nowiki>{{Keine}}</nowiki> und\n<pre>{{AuchNicht}}</pre>\n<code>{{Doch}}</code>")
    assert out.count("wv-template") == 1  # nur in <code> wertet MediaWiki Vorlagen aus
    assert "{{Keine}}" in out and "{{AuchNicht}}" in out and "{{Doch}}" in out


@requires_pandoc
def test_wiki_local_image(examples):
    out = wiki("[[Datei:bilder/beispiel.png|Grafik]]", examples)
    assert 'src="data:image/png;base64,' in out


def test_protect_templates_unit():
    text, mapping = protect_templates("a {{X|{{Y}}}} b <nowiki>{{Z}}</nowiki> {{ offen")
    assert len(mapping) == 1
    assert list(mapping.values()) == ["X"]
    assert "<nowiki>{{Z}}</nowiki>" in text
    assert text.endswith("{{ offen")
    marker = next(iter(mapping))
    html = restore_templates(f'<p>{marker}</p><a href="{marker}">x</a>', mapping)
    assert '<span class="wv-template"' in html
    assert 'href="{{X}}"' in html


def test_template_name_is_escaped():
    _, mapping = protect_templates("{{<script>alert(1)</script>}}")
    marker = next(iter(mapping))
    html = restore_templates(marker, mapping)
    assert "<script>" not in html and "&lt;script&gt;" in html


@pytest.mark.parametrize("fmt", ["md"])
def test_examples_render(examples, fmt):
    out = render_document((examples / "example.md").read_text("utf-8"), fmt, examples)
    assert "<h1" in out and "<table>" in out and "data:image/png" in out
