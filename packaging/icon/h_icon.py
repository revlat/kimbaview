"""Programm-Icon (Entwurf H): großer getigerter Katzenkopf über einem schmalen Papierstreifen."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d_icon as D  # noqa: E402


M = D.M


def variant_h(simple=False):
    img = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    D.bg(img)
    cx, cy, r = 512, 492, 345
    D.tabby_head(img, cx, cy, r, detail=not simple)
    d = ImageDraw.Draw(img)
    # schmaler Papierstreifen unter dem Kinn
    x0, y0, x1, y1, fold = 290, 790, 734, 950, 0 if simple else 56
    d.polygon([(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)], fill=D.WHITE)
    if fold:
        d.polygon([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=D.FOLD)
    if simple:
        d.rounded_rectangle([345, 850, 679, 905], radius=26, fill=D.HEAD)
    else:
        d.rounded_rectangle([345, 850, 560, 892], radius=21, fill=D.HEAD)
        d.rounded_rectangle([590, 856, 660, 886], radius=15, fill=D.LINE)
    for px in (322, 702):
        D.paw(d, px, 800, 86, 54)
    return img
