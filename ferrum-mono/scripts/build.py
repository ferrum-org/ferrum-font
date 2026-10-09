"""Paper Mono (Latin) + Geist Mono (Cyrillic), adapted to Paper's metrics.

GEIST is Geist Mono's variable font. For every Paper weight the Geist instance
is chosen whose stems, after the horizontal squeeze, match Paper's own stems,
so the Cyrillic carries the same colour as the Latin in every weight."""
import sys, os
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import RecordingPen, DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._g_l_y_f import Glyph

PAPER_DIR, GEIST, OUT_DIR = sys.argv[1:4]
WEIGHTS = ["Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold"]
CYR = [u for u in range(0x0400, 0x0530)]
FAMILY = "Paper Mono Cyr"

# Geist -> Paper vertical metrics. Geist's x-height grows with weight (530..540),
# so G_X is measured on each instance; the rest is constant in both families.
P_X = 509                    # x-height
G_ASC, P_ASC = 710, 747      # lowercase ascender
G_DSC, P_DSC = -150, -182    # descender
CAP = 710                    # cap height, the same in both
OVER = 20                    # overshoot band around the zone edges
XSCALE = 0.97                # Paper letters are ~3% narrower inside the cell


def map_y(y, lower, g_x):
    if y < -OVER:
        return -12 + (y + 12) * (P_DSC + 12) / (G_DSC + 12)
    if y < 0:
        # round bottoms: Geist caps overshoot 17, Paper 12; lowercase 12 in both
        return y if lower else y * 12 / 17
    if not lower:
        if y <= CAP:
            return y
        if y <= CAP + OVER:
            return CAP + (y - CAP) * 12 / 17
        return y - 5
    if y <= g_x:
        return y * P_X / g_x
    if y <= g_x + OVER:
        # x-height overshoot keeps its size (12 in both)
        return P_X + (y - g_x)
    if y <= G_ASC:
        return P_X + OVER + (y - g_x - OVER) * (P_ASC - P_X - OVER) / (G_ASC - g_x - OVER)
    return P_ASC + (y - G_ASC)


def transform(rec, lower, g_adv, p_adv, g_x):
    cx_g, cx_p = g_adv / 2, p_adv / 2
    f = lambda pt: (round(cx_p + (pt[0] - cx_g) * XSCALE), round(map_y(pt[1], lower, g_x)))
    out = []
    for op, args in rec:
        out.append((op, tuple(f(p) if p is not None else None for p in args)))
    return out


def stem(font, ch, y=250):
    """Width of the leftmost ink run at height y."""
    p = skPathFromGlyph(font.getBestCmap()[ord(ch)], font.getGlyphSet())
    band = pathops.Path()
    band.moveTo(-500, y - 0.5); band.lineTo(1500, y - 0.5); band.lineTo(1500, y + 0.5); band.lineTo(-500, y + 0.5); band.close()
    s = pathops.op(p, band, pathops.PathOp.INTERSECTION, fix_winding=True)
    return min((c.bounds[0], c.bounds[2] - c.bounds[0]) for c in s.contours)[1]


def vstroke(font, ch, x):
    """Thickness of the topmost ink run at x (a horizontal bar)."""
    p = skPathFromGlyph(font.getBestCmap()[ord(ch)], font.getGlyphSet())
    band = pathops.Path()
    band.moveTo(x - 0.5, -500); band.lineTo(x - 0.5, 1500); band.lineTo(x + 0.5, 1500); band.lineTo(x + 0.5, -500); band.close()
    s = pathops.op(p, band, pathops.PathOp.INTERSECTION, fix_winding=True)
    return max((c.bounds[3], c.bounds[3] - c.bounds[1]) for c in s.contours)[1]


def embolden(glyph, dx, dy):
    """Thicken strokes by dx (vertical stems) and dy (horizontal bars), each
    edge moving outward by half (FreeType-style, on the control polygon of a
    clockwise TrueType outline). Bars then grow inward only: the band from the
    baseline to the x-height is fitted back to [0, P_X], everything below and
    above is shifted by the same half amount, so all heights stay put."""
    if not (dx or dy) or glyph.numberOfContours <= 0:
        return
    pts = [tuple(map(float, p)) for p in glyph.coordinates]
    out = list(pts)
    start = 0
    for end in glyph.endPtsOfContours:
        n = end - start + 1
        for i in range(n):
            a, b, c = pts[start + (i - 1) % n], pts[start + i], pts[start + (i + 1) % n]
            def normal(p, q):
                tx, ty = q[0] - p[0], q[1] - p[1]
                L = (tx * tx + ty * ty) ** 0.5 or 1
                return -ty / L, tx / L          # left of travel = outside for clockwise
            n1, n2 = normal(a, b), normal(b, c)
            d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            if d < 0.2:
                continue                       # cusp: leave it
            sx, sy = (n1[0] + n2[0]) / d, (n1[1] + n2[1]) / d
            out[start + i] = (b[0] + sx * dx / 2, b[1] + sy * dy / 2)
        start = end + 1
    h = dy / 2
    def fit(y):
        if y < -h:
            return y + h
        if y > P_X + h:
            return y - h
        return (y + h) * P_X / (P_X + dy)
    glyph.coordinates = type(glyph.coordinates)([(round(x), round(fit(y))) for x, y in out])


def geist_for(P):
    """Geist instance whose п stem, squeezed by XSCALE, equals Paper's n stem."""
    target = stem(P, "n")
    lo, hi = 100.0, 900.0
    for _ in range(14):
        mid = (lo + hi) / 2
        g = instantiateVariableFont(TTFont(GEIST), {"wght": mid})
        if stem(g, "п") * XSCALE < target:
            lo = mid
        else:
            hi = mid
    wght = round((lo + hi) / 2, 1)
    return instantiateVariableFont(TTFont(GEIST), {"wght": wght}), wght


def outline(gs, name):
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    return pen.value


def build(weight):
    P = TTFont(os.path.join(PAPER_DIR, f"PaperMono-{weight}.ttf"))
    G, wght = geist_for(P)
    pc, gc = P.getBestCmap(), G.getBestCmap()
    gg = G["glyf"][gc[ord("x")]]
    gg.recalcBounds(G["glyf"])
    g_x = gg.yMax
    # Geist's heavy weights have more contrast than Paper's: its lowercase bars
    # (т) come out lighter than Paper's z, its three-stem letters (ш) lighter
    # than Paper's m. The difference is added back to the Geist-drawn lowercase.
    g_adv0 = G["hmtx"][gc[0x61]][0]
    # embolden() fits the bars back into the x-height, which takes some of the
    # added weight away again: solve (t + d) * P_X / (P_X + d) = target for d.
    t, target = vstroke(G, "т", g_adv0 * 0.2) * P_X / g_x, vstroke(P, "z", 300)
    bar_dy = max(0, round(P_X * (target - t) / (P_X - target)))
    m_dx = max(0, round(stem(P, "m") - stem(G, "ш") * XSCALE))
    pgs, ggs = P.getGlyphSet(), G.getGlyphSet()
    p_adv = P["hmtx"][pc[0x61]][0]
    g_adv = G["hmtx"][gc[0x61]][0]

    # Geist Latin outlines keyed by shape, to spot Cyrillic letters that are
    # drawn identically to Latin ones (А=A, о=o, ё=ë ...): those take Paper's glyph.
    latin_by_shape = {}
    for u in sorted(gc):
        if u < 0x250 and u in pc:
            latin_by_shape.setdefault(repr(outline(ggs, gc[u])), u)

    glyf, hmtx, cmap_tables = P["glyf"], P["hmtx"], [t for t in P["cmap"].tables if t.isUnicode()]
    reused = new = 0
    for u in CYR:
        if u not in gc or u in pc:
            continue
        gname = f"uni{u:04X}"
        shape = repr(outline(ggs, gc[u]))
        twin = latin_by_shape.get(shape)
        if twin is not None:
            src = outline(pgs, pc[twin])
            reused += 1
        else:
            ch = chr(u)
            lower = ch.islower() or u in (0x0459, 0x045A)
            src = transform(outline(ggs, gc[u]), lower, g_adv, p_adv, g_x)
            new += 1
        pen = TTGlyphPen(None)
        for op, args in src:
            getattr(pen, op)(*args)
        glyph = pen.glyph()
        if twin is None and lower:
            embolden(glyph, m_dx if ch in "шщы" else 0, bar_dy)
        glyf[gname] = glyph
        glyph.recalcBounds(glyf)
        hmtx[gname] = (p_adv, getattr(glyph, "xMin", 0))
        for t in cmap_tables:
            if t.format in (4, 12) or t.format == 4:
                t.cmap[u] = gname

    order = list(glyf.glyphOrder)
    P.setGlyphOrder(order)
    P["maxp"].numGlyphs = len(order)
    if "post" in P and P["post"].formatType == 2.0:
        P["post"].extraNames = []
        P["post"].mapping = {}
    # Fix format-4 cmap limits (BMP only, fine for Cyrillic)
    # Rename family
    name = P["name"]
    ps_weight = weight
    for rec in list(name.names):
        if rec.nameID in (1, 16):
            rec.string = FAMILY if rec.nameID == 16 or weight in ("Regular", "Bold") else f"{FAMILY} {weight}"
        elif rec.nameID == 4:
            rec.string = f"{FAMILY} {weight}"
        elif rec.nameID == 6:
            rec.string = f"PaperMonoCyr-{ps_weight}"
        elif rec.nameID == 3:
            rec.string = f"PaperMonoCyr-{ps_weight};custom-build"
    # OS/2 code page / unicode range: add Cyrillic
    os2 = P["OS/2"]
    os2.ulUnicodeRange1 |= 1 << 9
    os2.ulCodePageRange1 |= 1 << 2
    out = os.path.join(OUT_DIR, f"PaperMonoCyr-{weight}.ttf")
    P.save(out)
    return out, f"geist wght {wght}, bars +{bar_dy}, шщы stems +{m_dx}", reused, new


os.makedirs(OUT_DIR, exist_ok=True)
for w in WEIGHTS:
    print(build(w))
