"""Erzeugt das Programm-Icon in allen benötigten Formaten (benötigt Pillow).

    pip install pillow
    python packaging/make_icons.py

Motiv: Kimba (Entwurf H), eine getigerte Katze mit großem Kopf, schaut über einen
Papierstreifen. Für kleine Größen (≤ 32 px) wird die vereinfachte Fassung ohne Gesichts-
details und Textzeilen verwendet, damit das Icon in Taskleiste und Explorer klar bleibt.
Die Zeichenfunktionen liegen in packaging/icon (d_icon.py, h_icon.py).

Ausgabe:
  src/kimbaview/assets/kimbaview.ico   Windows (.exe, Fenster, Installer), 16–256 px
  src/kimbaview/assets/kimbaview.png   256 px (Fenster unter Linux)
  packaging/linux/kimbaview.png       256 px (Startmenü/„Öffnen mit“)
  packaging/macos/kimbaview.icns      macOS-App (1024 px)
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packaging" / "icon"))
from h_icon import variant_h  # noqa: E402

SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
SMALL_MAX = 32


def main() -> None:
    full, simple = variant_h(False), variant_h(True)
    images = [(simple if s <= SMALL_MAX else full).resize((s, s), Image.LANCZOS) for s in SIZES]

    assets = ROOT / "src" / "kimbaview" / "assets"
    big = images[-1]
    # BMP statt PNG in der .ico: Ältere Windows-Programmteile (GDI/WinForms, damit auch
    # pywebviews Fenster-Icon) lesen kleine PNG-komprimierte Icons sonst als Pixelrauschen.
    big.save(assets / "kimbaview.ico", format="ICO", sizes=[(s, s) for s in SIZES],
             append_images=images[:-1], bitmap_format="bmp")
    big.save(assets / "kimbaview.png")
    big.save(ROOT / "packaging" / "linux" / "kimbaview.png")
    full.save(ROOT / "packaging" / "macos" / "kimbaview.icns")
    # Icon für die Anleitung (README-Titel)
    images[-2].save(ROOT / "docs" / "kimbaview-icon.png")  # 128 px, im README auf 64 px angezeigt
    print("Icons erzeugt:", ", ".join(str(s) for s in SIZES))


if __name__ == "__main__":
    main()
