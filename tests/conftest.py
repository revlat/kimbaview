from pathlib import Path

import pytest

from kimbaview import i18n
from kimbaview.render_mediawiki import find_pandoc


@pytest.fixture(autouse=True)
def _german_ui():
    """Die meisten Tests prüfen deutsche Texte – unabhängig von der Systemsprache
    (die Build-Pipeline läuft auf englischen Systemen). Englisch prüft test_i18n.py."""
    i18n.set_language("de")
    yield
    i18n.set_language("de")

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

requires_pandoc = pytest.mark.skipif(find_pandoc() is None, reason="Pandoc nicht installiert")


@pytest.fixture
def examples() -> Path:
    return EXAMPLES
