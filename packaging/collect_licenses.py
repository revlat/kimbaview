"""Erzeugt THIRD-PARTY-LICENSES.txt mit den Lizenztexten aller gebündelten Pakete.

MIT/BSD verlangen, dass Copyright-Hinweis und Lizenztext bei der Weitergabe
mitgeliefert werden; Apache-2.0 (watchdog) zusätzlich die Lizenz selbst.
Aufruf:  python packaging/collect_licenses.py <ausgabedatei>
"""

from __future__ import annotations

import sys
import sysconfig
from importlib.metadata import PackageNotFoundError, distribution, requires
from pathlib import Path

SKIP = {"kimbaview", "pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile",
        "pywin32-ctypes", "setuptools", "packaging", "pip", "pytest", "pluggy", "iniconfig",
        "colorama"}


def _name(req: str) -> str:
    for sep in " ;[<>=!~(":
        req = req.split(sep, 1)[0]
    return req.strip()


def runtime_dists() -> list[str]:
    seen: dict[str, None] = {}
    stack = ["kimbaview"]
    while stack:
        name = stack.pop()
        key = name.lower().replace("_", "-")
        if key in seen:
            continue
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            continue
        seen[key] = None
        for req in requires(name) or []:
            if "extra ==" in req:
                continue
            stack.append(_name(req))
        del dist
    return sorted(k for k in seen if k not in SKIP)


# Ergänzungen für Inhalte, deren Lizenztext nicht in den Paketmetadaten steckt.
EXTRA = Path(__file__).resolve().parent / "licenses"


def supplements(name: str) -> list[tuple[str, str]]:
    """Zusätzliche Lizenztexte zu einem Paket aus packaging/licenses/."""
    out: list[tuple[str, str]] = []
    if name == "proxy-tools":
        out.append(("proxy-tools-NOTICE.txt", (EXTRA / "proxy-tools-NOTICE.txt").read_text(encoding="utf-8")))
    if name == "pywebview":
        # pywebview liefert die WebView2-DLLs von Microsoft mit (Windows-Backend).
        lib = Path(distribution(name).locate_file("webview/lib"))
        if any(lib.rglob("*WebView2*.dll")):
            for f in ("WebView2-LICENSE.txt", "WebView2-NOTICE.txt"):
                out.append((f"Microsoft WebView2 SDK – {f}", (EXTRA / f).read_text(encoding="utf-8")))
    return out


def license_texts(name: str) -> tuple[str, str, list[tuple[str, str]]]:
    dist = distribution(name)
    meta = dist.metadata
    lic = meta.get("License-Expression") or ""
    if not lic:
        raw = (meta.get("License") or "").strip()
        lic = raw.splitlines()[0] if raw else ""
    if not lic:
        cls = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License")]
        lic = ", ".join(cls)
    texts = []
    for f in dist.files or []:
        s = str(f)
        if ".dist-info" in s and any(k in s.upper() for k in ("LICEN", "COPYING", "NOTICE", "AUTHORS")):
            try:
                texts.append((Path(s).name, Path(dist.locate_file(f)).read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass
    texts += supplements(name.lower().replace("_", "-"))
    return dist.version, lic or "siehe Paket", texts


def python_license() -> str | None:
    stdlib = Path(sysconfig.get_paths()["stdlib"])  # macOS/Linux: lib/pythonX.Y/LICENSE.txt
    for cand in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE",
                 stdlib / "LICENSE.txt"):
        if cand.is_file():
            return cand.read_text(encoding="utf-8", errors="replace")
    return None


def main(out: str) -> None:
    parts = [
        "Fremdlizenzen / Third-party licenses",
        "=" * 72,
        "kimbaview enthält in der gebauten Fassung die folgenden Komponenten.",
        "Pandoc wird NICHT mitgeliefert, sondern als separates Programm aufgerufen.",
        "",
    ]
    py = python_license()
    if py:
        parts += ["-" * 72, f"Python {sys.version.split()[0]}  (PSF License)", "-" * 72, py, ""]
    for name in runtime_dists():
        version, lic, texts = license_texts(name)
        parts += ["-" * 72, f"{name} {version}  ({lic})", "-" * 72]
        if texts:
            for fname, text in texts:
                parts += [f"[{fname}]", text.strip(), ""]
        else:
            parts += ["(Kein Lizenztext im Paket enthalten; Lizenz laut Paketmetadaten: " + lic + ")", ""]
    Path(out).write_text("\n".join(parts), encoding="utf-8")
    print(f"{out}: {len(runtime_dists())} Pakete")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "THIRD-PARTY-LICENSES.txt")
