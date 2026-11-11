"""MediaWiki → HTML über Pandoc.

Sicherheit beim Pandoc-Aufruf
* ausschließlich ``subprocess.run`` mit Argumentliste, nie ``shell=True``
* Eingabe über stdin, Ausgabe über stdout – Pandoc bekommt keinen Dateipfad
* Zeitlimit 10 s (Prozess wird danach beendet)
* keine Filter, keine Lua-Skripte, kein ``--standalone``, keine Templates,
  kein ``--embed-resources``; zusätzlich ``--sandbox`` (ab Pandoc 2.15), das
  Pandoc jeglichen Datei- und Netzwerkzugriff verbietet.

Vorlagen ({{...}}) kann Pandoc nicht auflösen und lässt sie kommentarlos weg.
Wir ersetzen sie daher vorher durch eindeutige Marker und setzen danach einen
sichtbaren Platzhalter mit dem Vorlagennamen ein.
"""

from __future__ import annotations

import html as html_mod
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from kimbaview.highlight import highlight_code
from kimbaview.i18n import t
from kimbaview.sanitize import TEMPLATE_CLASS

PANDOC_TIMEOUT = 10.0


class PandocError(RuntimeError):
    pass


class PandocNotFoundError(PandocError):
    pass


class PandocTimeoutError(PandocError):
    pass


def pandoc_install_hint(platform: str | None = None) -> str:
    platform = platform or sys.platform
    key = {"win32": "pandoc.how_windows", "darwin": "pandoc.how_macos"}.get(platform, "pandoc.how_linux")
    return t("pandoc.missing", how=t(key))


def _candidate_paths() -> list[Path]:
    """Übliche Installationsorte – GUI-Programme erben oft einen kurzen PATH
    (z. B. macOS-Apps aus dem Finder kennen /opt/homebrew/bin nicht)."""
    if sys.platform == "win32":
        bases = [os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles")]
        return [Path(b) / "Pandoc" / "pandoc.exe" for b in bases if b]
    return [
        Path("/opt/homebrew/bin/pandoc"),
        Path("/usr/local/bin/pandoc"),
        Path("/usr/bin/pandoc"),
        Path.home() / ".local" / "bin" / "pandoc",
    ]


def find_pandoc() -> str | None:
    found = shutil.which("pandoc")
    if found:
        return found
    for cand in _candidate_paths():
        if cand.is_file():
            return str(cand)
    return None


def _popen_kwargs() -> dict:
    kwargs: dict = {"shell": False, "cwd": tempfile.gettempdir()}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # kein Konsolenfenster
    return kwargs


@lru_cache(maxsize=8)
def pandoc_version(pandoc: str) -> tuple[int, ...]:
    try:
        proc = subprocess.run(
            [pandoc, "--version"], capture_output=True, timeout=PANDOC_TIMEOUT, **_popen_kwargs()
        )
    except (OSError, subprocess.SubprocessError):
        return (0,)
    m = re.search(rb"pandoc(?:\.exe)?\s+(\d+(?:\.\d+)*)", proc.stdout)
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split(b"."))


def build_pandoc_command(pandoc: str, version: tuple[int, ...]) -> list[str]:
    cmd = [pandoc]
    if version >= (2, 15):
        cmd.append("--sandbox")
    cmd += ["--from=mediawiki", "--to=html5", "--wrap=none"]
    # Pandoc soll keinen Code hervorheben – das übernimmt Pygments einheitlich.
    cmd.append("--syntax-highlighting=none" if version >= (3, 8) else "--no-highlight")
    return cmd


def run_pandoc(text: str, pandoc: str | None = None, timeout: float = PANDOC_TIMEOUT) -> str:
    pandoc = pandoc or find_pandoc()
    if not pandoc:
        raise PandocNotFoundError(pandoc_install_hint())
    cmd = build_pandoc_command(pandoc, pandoc_version(pandoc))
    try:
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
            **_popen_kwargs(),
        )
    except subprocess.TimeoutExpired:
        raise PandocTimeoutError(
            t("pandoc.timeout", timeout=timeout)
        ) from None
    except FileNotFoundError:
        raise PandocNotFoundError(pandoc_install_hint()) from None
    except OSError as exc:
        raise PandocError(t("pandoc.start_failed", error=exc)) from None
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()[:1000]
        raise PandocError(t("pandoc.failed", code=proc.returncode, error=err))
    return proc.stdout.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- Vorlagen

# Bereiche, in denen {{...}} kein Vorlagenaufruf ist.
_SKIP_OPEN_RE = re.compile(
    r"<!--|<(nowiki|pre|syntaxhighlight|source|math)\b[^>]*?(/?)>", re.IGNORECASE
)
MAX_TEMPLATE_NAME = 80


def _template_name(inner: str) -> str:
    name = inner.split("|", 1)[0]
    name = re.sub(r"\s+", " ", name.lstrip("{")).strip()
    if len(name) > MAX_TEMPLATE_NAME:
        name = name[: MAX_TEMPLATE_NAME - 1] + "…"
    return name or "?"


def protect_templates(text: str) -> tuple[str, dict[str, str]]:
    """Ersetzt Vorlagen durch Marker. Liefert (neuer Text, Marker → Vorlagenname)."""
    nonce = secrets.token_hex(6)
    mapping: dict[str, str] = {}
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        brace = text.find("{{", i)
        skip = _SKIP_OPEN_RE.search(text, i)
        if brace == -1:
            out.append(text[i:])
            break
        if skip and skip.start() < brace:
            # geschützten Bereich unverändert übernehmen
            if skip.group(0) == "<!--":
                end = text.find("-->", skip.end())
                end = n if end == -1 else end + 3
            elif skip.group(2) == "/":  # <nowiki/> o. Ä.
                end = skip.end()
            else:
                close = re.compile(rf"</{skip.group(1)}\s*>", re.IGNORECASE).search(text, skip.end())
                end = n if close is None else close.end()
            out.append(text[i:end])
            i = end
            continue
        # balanciertes Ende suchen (verschachtelte Vorlagen)
        depth, j = 1, brace + 2
        while j < n and depth:
            if text.startswith("{{", j):
                depth += 1
                j += 2
            elif text.startswith("}}", j):
                depth -= 1
                j += 2
            else:
                j += 1
        if depth:  # nicht geschlossen (z. B. beim Tippen) → unverändert lassen
            out.append(text[i:])
            break
        marker = f"WVTPL{nonce}N{len(mapping)}X"
        mapping[marker] = _template_name(text[brace + 2 : j - 2])
        out.append(text[i:brace])
        out.append(marker)
        i = j
    return "".join(out), mapping


_HTML_TAG_RE = re.compile(r"<[^<>]*>")


def restore_templates(html: str, mapping: dict[str, str]) -> str:
    if not mapping:
        return html
    marker_re = re.compile("|".join(re.escape(m) for m in sorted(mapping, key=len, reverse=True)))

    def plain(m: re.Match[str]) -> str:
        return html_mod.escape("{{" + mapping[m.group(0)] + "}}", quote=True)

    def span(m: re.Match[str]) -> str:
        label = html_mod.escape("{{" + mapping[m.group(0)] + "}}", quote=False)
        return (
            f'<span class="{TEMPLATE_CLASS}" title="{html_mod.escape(t("template.title"), quote=True)}">'
            f"{label}</span>"
        )

    # In Tag-Attributen nur Text einsetzen, sonst würde HTML zerbrochen.
    html = _HTML_TAG_RE.sub(lambda t: marker_re.sub(plain, t.group(0)), html)
    return marker_re.sub(span, html)


# ----------------------------------------------------------------------- Codeblöcke

_PANDOC_CODE_RE = re.compile(r'<pre(?: class="([^"]*)")?><code>(.*?)</code></pre>', re.DOTALL)


def _highlight_blocks(html: str) -> str:
    def repl(m: re.Match[str]) -> str:
        classes = (m.group(1) or "").split()
        lang = next((c for c in classes if c not in ("sourceCode", "numberLines")), None)
        return highlight_code(html_mod.unescape(m.group(2)), lang)

    return _PANDOC_CODE_RE.sub(repl, html)


def render_mediawiki(text: str, pandoc: str | None = None, timeout: float = PANDOC_TIMEOUT) -> str:
    protected, mapping = protect_templates(text)
    html = run_pandoc(protected, pandoc=pandoc, timeout=timeout)
    html = _highlight_blocks(html)
    return restore_templates(html, mapping)
