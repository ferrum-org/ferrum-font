"""Area-based side-space measurement (HT Letterspacer style) for a mono font."""
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph

CAP, XH = 710, 509


def profile(font, name, y0, y1, step=10):
    """Leftmost/rightmost ink per scanline in [y0, y1]."""
    p = skPathFromGlyph(name, font.getGlyphSet())
    rows = []
    for y in range(int(y0) + step // 2, int(y1), step):
        band = pathops.Path()
        band.moveTo(-500, y - 1); band.lineTo(-500, y + 1); band.lineTo(1500, y + 1); band.lineTo(1500, y - 1); band.close()
        s = pathops.op(p, band, pathops.PathOp.INTERSECTION, fix_winding=True)
        b = s.bounds
        rows.append(None if b is None or b == (0, 0, 0, 0) or s.area == 0 else (b[0], b[2]))
    return rows


def side_spaces(font, name, upper, depth):
    adv = font["hmtx"][name][0]
    top = CAP if upper else XH
    rows = profile(font, name, 0, top)
    ink = [r for r in rows if r]
    if not ink:
        return None
    xmin = min(r[0] for r in ink); xmax = max(r[1] for r in ink)
    L = R = 0.0
    for r in rows:
        if r is None:
            L += depth; R += depth
        else:
            L += min(r[0] - xmin, depth)
            R += min(xmax - r[1], depth)
    n = len(rows)
    # average white per scanline, plus the plain sidebearings
    return xmin + L / n, (adv - xmax) + R / n, xmin, adv - xmax


def imbalance(font, name, upper, depth):
    s = side_spaces(font, name, upper, depth)
    if s is None:
        return None
    return (s[1] - s[0]) / 2  # positive: glyph should move right
