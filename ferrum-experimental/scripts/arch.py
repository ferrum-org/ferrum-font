"""Diagonal entry strokes at the top of lowercase l and r.

l: the flat horizontal at the ascender top-left becomes a curved diagonal —
   the on-curve corner turns into an off-curve guide, sweeping from the inner
   bay up to the stem top with a pointed tip at the left.

r: the flat arm shelf (top-left corner at x-height) is lowered to create a
   straight diagonal from the pointed left tip up to the right end of the arm.
   The point stays on-curve (no flag change), so the outline stays polygonal
   and avoids curvature artifacts at the arm-shoulder junction.

No points are added or removed, only one coordinate (and for l, one flag) per
letter change, so variable masters stay point-compatible.

Must run after fix.py, before chisel.py.
Usage: arch.py DIR [--variable]
"""
import sys, glob
from fontTools.ttLib import TTFont

GUIDE = 0.62   # tip sits 62% of the way from inner_y up to top_y


def _top_left_idx(coords, flags):
    """Index of the on-curve corner at (leftmost x, maximum y): the top-left
    corner of the l stem, before the flat horizontal leading to the right."""
    max_y = max(y for x, y in coords)
    cands = [i for i, (x, y) in enumerate(coords)
             if abs(y - max_y) < 2 and (flags[i] & 1)]
    return min(cands, key=lambda i: coords[i][0]) if cands else None


def _xh_left_idx(coords, flags, xh):
    """Index of the leftmost on-curve point that lies on a straight horizontal
    at y ≈ xh (the arm-shelf of r)."""
    n = len(coords)
    best = None
    for i in range(n):
        if not (flags[i] & 1):
            continue
        x, y = coords[i]
        if abs(y - xh) > 6:
            continue
        for di in (-1, 1):
            j = (i + di) % n
            if (flags[j] & 1) and abs(coords[j][1] - y) < 2:
                if best is None or x < coords[best][0]:
                    best = i
    return best


def _apply_l(g, glyf):
    """l: off-curve bezier sweep — top-left corner → off-curve guide."""
    coords = list(g.coordinates)
    flags = bytearray(g.flags)

    idx = _top_left_idx(coords, flags)
    if idx is None:
        return False

    x, top_y = coords[idx]
    n = len(coords)
    inner_y = None
    for di in (-1, 1):
        j = (idx + di) % n
        if (flags[j] & 1) and coords[j][1] < top_y - 4:
            inner_y = coords[j][1]
            break
    if inner_y is None:
        return False

    guide_y = round(inner_y + (top_y - inner_y) * GUIDE)
    flags[idx] = flags[idx] & ~1    # on-curve → off-curve
    coords[idx] = (x, guide_y)

    g.coordinates = type(g.coordinates)(coords)
    g.flags = flags
    return True


def _apply_r(g, glyf, xh):
    """r: straight diagonal shelf — top-left arm corner lowered, stays on-curve."""
    coords = list(g.coordinates)
    flags = bytearray(g.flags)

    idx = _xh_left_idx(coords, flags, xh)
    if idx is None:
        return False

    x, top_y = coords[idx]
    n = len(coords)
    inner_y = None
    for di in (-1, 1):
        j = (idx + di) % n
        if (flags[j] & 1) and coords[j][1] < top_y - 4:
            inner_y = coords[j][1]
            break
    if inner_y is None:
        return False

    tip_y = round(inner_y + (top_y - inner_y) * GUIDE)
    coords[idx] = (x, tip_y)       # on-curve flag unchanged

    g.coordinates = type(g.coordinates)(coords)
    g.flags = flags
    return True


def process(path):
    f = TTFont(path)
    glyf_table = f["glyf"]
    cm = f.getBestCmap()
    xh = f["OS/2"].sxHeight
    changed = 0

    for ch, fn, kw in (
        ("l", _apply_l, {}),
        ("r", _apply_r, {"xh": xh}),
    ):
        if ord(ch) not in cm:
            continue
        name = cm[ord(ch)]
        g = glyf_table[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        g.expand(glyf_table)
        if fn(g, glyf_table, **kw):
            g.recalcBounds(glyf_table)
            f["hmtx"][name] = (f["hmtx"][name][0], getattr(g, "xMin", 0))
            changed += 1

    if changed:
        f.save(path)
    return changed


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    n = process(p)
    print("arch:", p.split("/")[-1].split("\\")[-1], "—", n, "glyphs")
