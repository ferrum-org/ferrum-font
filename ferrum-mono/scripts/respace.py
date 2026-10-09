"""Re-centre Cyrillic glyphs in the mono cell, using the side-space measure
calibrated on Paper's own Latin (depth 25: Paper's Latin sits within ±10 there).
Glyphs that are exact copies of Paper Latin letters keep Paper's placement."""
import sys, glob
sys.path.insert(0, sys.argv[2])
from spacing import side_spaces
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

DEPTH, THRESH = 25, 6
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def shape(f, name):
    p = DecomposingRecordingPen(f.getGlyphSet()); f.getGlyphSet()[name].draw(p); return repr(p.value)


def run(path):
    f = TTFont(path); cmap = f.getBestCmap(); glyf = f["glyf"]
    latin = {shape(f, cmap[u]) for u in cmap if u < 0x250 and chr(u).isalpha()}
    moved = {}
    for u in sorted(cmap):
        if not (0x400 <= u < 0x530):
            continue
        name = cmap[u]; ch = chr(u)
        if glyf[name].numberOfContours == 0 or shape(f, name) in latin or u == 0x041A:
            continue
        upper = ch.isupper() or not ch.islower()
        s = side_spaces(f, name, upper, DEPTH)
        if s is None:
            continue
        dx = round((s[1] - s[0]) / 2)
        if abs(dx) < THRESH:
            continue
        g = glyf[name]
        if g.isComposite():
            continue
        g.coordinates.translate((dx, 0))
        g.recalcBounds(glyf)
        f["hmtx"][name] = (f["hmtx"][name][0], g.xMin)
        for alt in [n for n in f.getGlyphOrder() if n.startswith(name + ".cv")]:
            ga = glyf[alt]; ga.coordinates.translate((dx, 0)); ga.recalcBounds(glyf)
            f["hmtx"][alt] = (f["hmtx"][alt][0], ga.xMin)
        moved[ch] = dx
    f.save(path)
    return moved


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    print(p.split("/")[-1], run(p))
