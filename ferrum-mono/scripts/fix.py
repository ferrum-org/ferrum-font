"""Targeted fixes for the Cyrillic in Paper Mono Cyr (applied after build.py).

- л, Л: left leg moved inward so the letter is no wider than н / П
- д, Д: body narrowed to the width of ц / Ц (left and right parts moved inward)
- Д, Ц, Щ: descending tails shortened to the length of the lowercase tails
Strokes are translated, never scaled, so stem thickness is unchanged.

Finally every Geist-drawn Cyrillic outline is run through skia-pathops:
overlaps removed (ћ), duplicate points and zero-length segments dropped,
contours clockwise. With --variable (masters of the variable font) the
outlines are left as drawn: the cleanup would give every weight a different
point structure, and a variable font needs them identical.
"""
import sys, glob
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph, ttfGlyphFromSkPath
from fontTools.pens.recordingPen import DecomposingRecordingPen


def bounds(font, u):
    g = font["glyf"][font.getBestCmap()[u]]
    g.recalcBounds(font["glyf"])
    return g.xMin, g.yMin, g.xMax, g.yMax


def edit(font, u, fn):
    glyf = font["glyf"]
    name = font.getBestCmap()[u]
    g = glyf[name]
    coords = g.coordinates
    for i in range(len(coords)):
        x, y = coords[i]
        coords[i] = tuple(round(v) for v in fn(x, y))
    g.recalcBounds(glyf)
    adv, _ = font["hmtx"][name]
    font["hmtx"][name] = (adv, g.xMin)


def fix(path):
    f = TTFont(path)
    mid = f["hmtx"]["uni043D"][0] / 2
    o = ord

    # л: no wider than н (the right stem sits further out than н's, so the
    # width is matched, not the left edge); respace.py re-centres it
    nb, lb = bounds(f, o("н")), bounds(f, o("л"))
    dx = (lb[2] - (nb[2] - nb[0])) - lb[0]
    edit(f, o("л"), lambda x, y: (x + dx if x < mid else x, y))
    # Л: same idea against П
    dx = (bounds(f, o("П"))[0] - 12) - bounds(f, o("Л"))[0]
    edit(f, o("Л"), lambda x, y: (x + dx if x < mid else x, y))

    # д / Д: match ц / Ц width
    for d, c in (("д", "ц"), ("Д", "Ц")):
        db, cb = bounds(f, o(d)), bounds(f, o(c))
        left = max(0, cb[0] - db[0])
        right = max(0, db[2] - cb[2])
        edit(f, o(d), lambda x, y, l=left, r=right: (x + l if x < mid else x - r, y))

    # Uppercase tails: same depth as lowercase tails
    low_tail = bounds(f, o("ц"))[1]
    for ch in "ДЦЩ":
        cap_tail = bounds(f, o(ch))[1]
        k = low_tail / cap_tail
        edit(f, o(ch), lambda x, y, k=k: (x, y * k if y < 0 else y))

    if VARIABLE:
        f.save(path)
        return

    # clean outlines; copies of Paper Latin letters stay identical
    def shape(name):
        pen = DecomposingRecordingPen(f.getGlyphSet()); f.getGlyphSet()[name].draw(pen); return repr(pen.value)
    cmap = f.getBestCmap()
    latin = {shape(cmap[u]) for u in cmap if u < 0x250 and chr(u).isalpha()}
    for u, name in sorted(cmap.items()):
        g = f["glyf"][name]
        if not (0x400 <= u < 0x530) or g.isComposite() or g.numberOfContours <= 0 or shape(name) in latin:
            continue
        p = pathops.simplify(skPathFromGlyph(name, f.getGlyphSet()), fix_winding=True, clockwise=True)
        ng = ttfGlyphFromSkPath(p)
        f["glyf"][name] = ng
        ng.recalcBounds(f["glyf"])
        f["hmtx"][name] = (f["hmtx"][name][0], ng.xMin)

    f.save(path)


VARIABLE = "--variable" in sys.argv[2:]
for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    fix(p)
    print("fixed", p)
