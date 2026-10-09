"""Check marks and crosses that CLIs and test runners print, which Paper Mono
does not have:  ✓ ✔ (U+2713, U+2714)  ✗ ✘ (U+2717, U+2718)  ✕ ✖ (U+2715, U+2716).

Drawn as strokes of the font's own stem weight (the heavy forms 1.7x), one
cell wide. Every glyph is built from explicit polygons -- the check mark one
offset polyline with a mitred corner, the crosses two overlapping strokes --
so the outlines have the same points in every weight and serve as masters of
the variable font as they are (pass --variable there; nothing differs).

    python3 symbols.py out [--variable]
"""
import sys, glob, math
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph
from fontTools.pens.ttGlyphPen import TTGlyphPen

CELL, SB = 606, 64
HEAVY = 1.7


def stem(f, ch="n", y=200):
    p = skPathFromGlyph(f.getBestCmap()[ord(ch)], f.getGlyphSet())
    b = pathops.Path(); b.moveTo(-500, y - .5); b.lineTo(1500, y - .5); b.lineTo(1500, y + .5); b.lineTo(-500, y + .5); b.close()
    s = pathops.op(p, b, pathops.PathOp.INTERSECTION, fix_winding=True)
    r = sorted((c.bounds[0], c.bounds[2]) for c in s.contours)
    return r[0][1] - r[0][0]


def clockwise(pts):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return pts if area < 0 else pts[::-1]          # y-up: negative area = clockwise


def stroke(a, b, t):
    """Parallelogram of perpendicular thickness t along a -> b, square ends."""
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy)
    nx, ny = -dy / L * t / 2, dx / L * t / 2
    return clockwise([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])


def polyline(pts, t):
    """Closed outline of a stroked polyline (one contour), mitred joins."""
    h = t / 2
    def off(p, q, s):
        dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy)
        return (-dy / L * h * s, dx / L * h * s)
    def side(s):
        out = []
        for i, p in enumerate(pts):
            if i == 0:
                o = off(pts[0], pts[1], s); out.append((p[0] + o[0], p[1] + o[1])); continue
            if i == len(pts) - 1:
                o = off(pts[-2], pts[-1], s); out.append((p[0] + o[0], p[1] + o[1])); continue
            o1, o2 = off(pts[i - 1], p, s), off(p, pts[i + 1], s)
            # intersection of the two offset lines
            a1 = (pts[i - 1][0] + o1[0], pts[i - 1][1] + o1[1]); d1 = (p[0] - pts[i - 1][0], p[1] - pts[i - 1][1])
            a2 = (p[0] + o2[0], p[1] + o2[1]); d2 = (pts[i + 1][0] - p[0], pts[i + 1][1] - p[1])
            det = d1[0] * d2[1] - d1[1] * d2[0]
            k = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / det
            out.append((a1[0] + d1[0] * k, a1[1] + d1[1] * k))
        return out
    return clockwise(side(1) + side(-1)[::-1])


def glyph(contours):
    pen = TTGlyphPen(None)
    for c in contours:
        pen.moveTo(tuple(map(round, c[0])))
        for p in c[1:]:
            pen.lineTo(tuple(map(round, p)))
        pen.closePath()
    return pen.glyph()


def build(path):
    f = TTFont(path)
    cmap = f.getBestCmap()
    t = stem(f)
    x0, x1 = SB, CELL - SB
    w = x1 - x0
    # One set of centre lines for every weight (also keeps the variable
    # masters compatible); only the stroke changes. Ends stay far enough from
    # the cell edge for the heaviest stroke.
    heavy = min(t * HEAVY, 200)
    y0, y1 = 20, 620                              # check marks, ballot crosses
    i = 46                                        # centre lines inset from the box
    X0, X1 = x0 + i, x1 - i
    mul = f["glyf"][cmap[0xD7]]; mul.recalcBounds(f["glyf"])
    my = (mul.yMin + mul.yMax) / 2

    def check(tk):
        a = (X0, y0 + (y1 - y0) * 0.42)
        v = (X0 + (X1 - X0) * 0.34, y0)
        b = (X1, y1)
        return [polyline([a, v, b], tk)]

    def ballot(tk):
        # a hand-made X: the strokes are not mirror images
        return [stroke((X0, y0), (X1 - 6, y1), tk),
                stroke((X0 + 24, y1 - 10), (X1, y0 + 10), tk)]

    def mult(tk):
        c, h = CELL / 2, (X1 - X0) * 0.42      # larger than the multiplication sign
        return [stroke((c - h, my - h), (c + h, my + h), tk), stroke((c - h, my + h), (c + h, my - h), tk)]

    made = 0
    for u, contours in ((0x2713, check(t)), (0x2714, check(heavy)),
                        (0x2717, ballot(t)), (0x2718, ballot(heavy)),
                        (0x2715, mult(t)), (0x2716, mult(heavy))):
        if u in cmap:
            continue
        name = f"uni{u:04X}"
        g = glyph(contours)
        f["glyf"][name] = g; g.recalcBounds(f["glyf"])
        f["hmtx"][name] = (CELL, g.xMin)
        if name not in f.getGlyphOrder():
            f.setGlyphOrder(f.getGlyphOrder() + [name])
        for st in f["cmap"].tables:
            if st.isUnicode():
                st.cmap[u] = name
        made += 1
    f.save(path)
    return made


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    print(p.replace("\\", "/").split("/")[-1], build(p), "symbols")
