"""Zeichenfunktionen für das Programm-Icon: Hintergrund, Dokument, getigerter Katzenkopf (Kimba), Pfoten."""
import math

from PIL import Image, ImageDraw

M = 1024
BLUE_T, BLUE_B = (47, 129, 247), (11, 61, 145)
WHITE, FOLD, HEAD, LINE = (255, 255, 255), (201, 216, 240), (31, 111, 235), (150, 164, 184)
FUR = (172, 116, 66)        # Grundfell braun
FUR_LIGHT = (205, 158, 108) # hellere Flanken
STRIPE = (70, 43, 24)       # Tigerstreifen
MUZZLE = (240, 222, 196)    # Schnauze/Kinn
EAR_IN = (232, 160, 160)
EYE = (164, 192, 72)
NOSE = (196, 110, 104)


def bg(img):
    g = Image.new("RGBA", (M, M)); d = ImageDraw.Draw(g)
    for y in range(M):
        t = y / (M - 1)
        d.line([(0, y), (M, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(BLUE_T, BLUE_B)) + (255,))
    mask = Image.new("L", (M, M), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, M - 40, M - 40], radius=200, fill=255)
    img.paste(g, (0, 0), mask)


def page(d, x0, y0, x1, y1, fold=140, lines=True):
    d.polygon([(x0, y0), (x1 - fold, y0), (x1, y0 + fold), (x1, y1), (x0, y1)], fill=WHITE)
    if fold:
        d.polygon([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=FOLD)
    if lines:
        d.rounded_rectangle([x0 + 70, y0 + 150, x0 + 330, y0 + 210], radius=22, fill=HEAD)
        for i, w in enumerate((380, 320, 380)):
            y = y0 + 260 + i * 72
            d.rounded_rectangle([x0 + 70, y, x0 + 70 + w, y + 38], radius=19, fill=LINE)


def bezier(p0, p1, p2, n=40):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in (i / n for i in range(n + 1))]


def tapered(d, pts, w0, w1, color):
    """Streifen entlang einer Linie, Breite verläuft von w0 nach w1 (spitz zulaufend)."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        a = pts[min(i + 1, n - 1)]; b = pts[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = (w0 + (w1 - w0) * i / (n - 1)) / 2
        left.append((x + nx * w, y + ny * w)); right.append((x - nx * w, y - ny * w))
    d.polygon(left + right[::-1], fill=color)


def head_mask(cx, cy, r):
    m = Image.new("L", (M, M), 0); d = ImageDraw.Draw(m)
    d.polygon([(cx - r * 0.98, cy - r * 0.1), (cx - r * 0.82, cy - r * 1.28), (cx - r * 0.18, cy - r * 0.78)], fill=255)
    d.polygon([(cx + r * 0.98, cy - r * 0.1), (cx + r * 0.82, cy - r * 1.28), (cx + r * 0.18, cy - r * 0.78)], fill=255)
    d.ellipse([cx - r, cy - r * 0.86, cx + r, cy + r * 0.86], fill=255)
    return m


def tabby_head(img, cx, cy, r, detail=True):
    mask = head_mask(cx, cy, r)
    fur = Image.new("RGBA", (M, M), FUR + (255,))
    d = ImageDraw.Draw(fur)
    # hellere Wangen/Flanken
    d.ellipse([cx - r * 1.05, cy - r * 0.05, cx - r * 0.35, cy + r * 0.9], fill=FUR_LIGHT)
    d.ellipse([cx + r * 0.35, cy - r * 0.05, cx + r * 1.05, cy + r * 0.9], fill=FUR_LIGHT)
    s = r / 230  # Skalierung relativ zum Entwurf
    W = 34 * s
    # --- Oberkopf: Bänder vom "M" nach hinten über den Kopf
    for off, bend in ((-0.32, -0.25), (-0.11, -0.06), (0.11, 0.06), (0.32, 0.25)):
        p0 = (cx + r * off * 0.8, cy - r * 0.42)
        p1 = (cx + r * (off + bend * 0.6), cy - r * 0.72)
        p2 = (cx + r * (off * 1.25 + bend), cy - r * 0.98)
        tapered(d, bezier(p0, p1, p2), W * 0.9, W * 0.25, STRIPE)
    # --- "M" auf der Stirn (geschwungen)
    tapered(d, bezier((cx - r * 0.42, cy - r * 0.26), (cx - r * 0.34, cy - r * 0.58), (cx - r * 0.18, cy - r * 0.46)), W * 0.35, W * 0.8, STRIPE)
    tapered(d, bezier((cx - r * 0.18, cy - r * 0.46), (cx - r * 0.06, cy - r * 0.36), (cx, cy - r * 0.5)), W * 0.8, W * 0.5, STRIPE)
    tapered(d, bezier((cx + r * 0.42, cy - r * 0.26), (cx + r * 0.34, cy - r * 0.58), (cx + r * 0.18, cy - r * 0.46)), W * 0.35, W * 0.8, STRIPE)
    tapered(d, bezier((cx + r * 0.18, cy - r * 0.46), (cx + r * 0.06, cy - r * 0.36), (cx, cy - r * 0.5)), W * 0.8, W * 0.5, STRIPE)
    # --- Seitenstreifen: vom Rand nach innen, der Kopfrundung folgend
    for sx in (-1, 1):
        for k, (ya, yb, ln) in enumerate(((-0.42, -0.30, 0.42), (-0.18, -0.08, 0.36), (0.06, 0.12, 0.32))):
            p0 = (cx + sx * r * 1.02, cy + r * ya)
            p1 = (cx + sx * r * (1.0 - ln * 0.55), cy + r * (ya + yb) / 2 - r * 0.05)
            p2 = (cx + sx * r * (1.0 - ln), cy + r * yb)
            tapered(d, bezier(p0, p1, p2), W * 1.0, W * 0.15, STRIPE)
        # Wangen-Schnörkel vom Augenwinkel nach außen
        p0 = (cx + sx * r * 0.52, cy + r * 0.02)
        p1 = (cx + sx * r * 0.72, cy + r * 0.12)
        p2 = (cx + sx * r * 0.86, cy + r * 0.34)
        tapered(d, bezier(p0, p1, p2), W * 0.55, W * 0.15, STRIPE)
        p0 = (cx + sx * r * 0.48, cy + r * 0.26)
        p1 = (cx + sx * r * 0.66, cy + r * 0.36)
        p2 = (cx + sx * r * 0.82, cy + r * 0.56)
        tapered(d, bezier(p0, p1, p2), W * 0.5, W * 0.12, STRIPE)
        # dunkler Ohrrand
        d.polygon([(cx + sx * r * 0.98, cy - r * 0.1), (cx + sx * r * 0.82, cy - r * 1.28),
                   (cx + sx * r * 0.88, cy - r * 0.5)], fill=STRIPE)
    if detail:
        # Ohren innen
        for sx in (-1, 1):
            d.polygon([(cx + sx * r * 0.74, cy - r * 0.5), (cx + sx * r * 0.74, cy - r * 1.02),
                       (cx + sx * r * 0.38, cy - r * 0.74)], fill=EAR_IN)
        # Schnauze, Augen, Nase
        d.ellipse([cx - r * 0.44, cy + r * 0.1, cx + r * 0.44, cy + r * 0.74], fill=MUZZLE)
        for sx in (-1, 1):
            ex = cx + sx * r * 0.36
            d.ellipse([ex - r * 0.2, cy - r * 0.2, ex + r * 0.2, cy + r * 0.13], fill=STRIPE)      # dunkle Augenumrandung
            d.ellipse([ex - r * 0.16, cy - r * 0.17, ex + r * 0.16, cy + r * 0.1], fill=EYE)
            d.ellipse([ex - r * 0.045, cy - r * 0.15, ex + r * 0.045, cy + r * 0.08], fill=(18, 18, 18))
            d.ellipse([ex + r * 0.02, cy - r * 0.12, ex + r * 0.07, cy - r * 0.07], fill=WHITE)   # Lichtpunkt
        d.polygon([(cx - r * 0.11, cy + r * 0.24), (cx + r * 0.11, cy + r * 0.24), (cx, cy + r * 0.36)], fill=NOSE)
        d.line([(cx, cy + r * 0.36), (cx, cy + r * 0.46)], fill=STRIPE, width=max(3, int(6 * s)))
    img.paste(fur, (0, 0), mask)


def paw(d, px, py, rw, rh):
    d.ellipse([px - rw, py - rh, px + rw, py + rh], fill=FUR)
    for o in (-0.45, 0.0, 0.45):
        tapered(d, bezier((px + rw * o - rw * 0.12, py - rh * 0.95), (px + rw * o, py - rh * 0.4), (px + rw * o + rw * 0.06, py)),
                rw * 0.22, rw * 0.05, STRIPE)


def variant_d(simple=False):
    img = Image.new("RGBA", (M, M), (0, 0, 0, 0)); bg(img)
    tabby_head(img, 512, 335, 205, detail=not simple)
    d = ImageDraw.Draw(img)
    page(d, 230, 470, 794, 930, fold=0 if simple else 130, lines=not simple)
    if simple:
        d.rounded_rectangle([310, 590, 714, 660], radius=30, fill=HEAD)
        d.rounded_rectangle([310, 730, 714, 800], radius=30, fill=LINE)
    for px in (352, 672):
        paw(d, px, 478, 66, 44)
    return img
