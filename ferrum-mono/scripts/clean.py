"""Remove Paper's logo glyph (U+F8FF), neutralise Paper-branded name strings,
label ss20, and make the font strictly monospaced:

- the 21 key-cap / arrow symbols Paper draws 1.25 cells wide (⌘ ⌥ ⏎ ⇧ ...)
  are scaled into the cell, so every mapped glyph is one cell wide and the
  font is listed as monospace everywhere (post.isFixedPitch, fontconfig);
- block elements (U+2580-259F) are stretched to the full line height, so
  ▀ ▄ █ stack without gaps.
The width-changing ss02 alternates (M W m w ...) are left as designed."""
import sys, glob
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen


def sort_features(f):
    """OpenType wants FeatureList sorted by tag; grafted features (ss20, cv02)
    are appended at the end, so sort and remap the LangSys indices."""
    for tag in ("GSUB", "GPOS"):
        if tag not in f:
            continue
        t = f[tag].table
        recs = t.FeatureList.FeatureRecord
        order = sorted(range(len(recs)), key=lambda i: recs[i].FeatureTag)
        new_index = {old: new for new, old in enumerate(order)}
        t.FeatureList.FeatureRecord = [recs[i] for i in order]
        for sr in t.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is None:
                    continue
                ls.FeatureIndex = sorted(new_index[i] for i in ls.FeatureIndex)
                if ls.ReqFeatureIndex != 0xFFFF:
                    ls.ReqFeatureIndex = new_index[ls.ReqFeatureIndex]


def redraw(f, name, matrix, adv):
    rec = DecomposingRecordingPen(f.getGlyphSet()); f.getGlyphSet()[name].draw(rec)
    pen = TTGlyphPen(None); rec.replay(TransformPen(pen, matrix))
    g = pen.glyph(); f["glyf"][name] = g; g.recalcBounds(f["glyf"])
    f["hmtx"][name] = (adv, getattr(g, "xMin", 0))
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.ttGlyphPen import TTGlyphPen

for p in sorted(glob.glob(sys.argv[1] + "/*.ttf")):
    f = TTFont(p)
    name = f.getBestCmap().get(0xF8FF)
    if name:
        for t in f["cmap"].tables:
            t.cmap.pop(0xF8FF, None)
        f["glyf"][name] = TTGlyphPen(None).glyph()      # empty outline, glyph kept for lookups
        f["hmtx"][name] = (f["hmtx"][name][0], 0)
    cmap = f.getBestCmap()
    cell = f["hmtx"][cmap[0x61]][0]
    if name:
        f["hmtx"][name] = (cell, 0)
    for u, g in sorted(cmap.items()):
        adv = f["hmtx"][g][0]
        if adv > cell:
            k = cell / adv                 # (x - adv/2) * k + cell/2
            redraw(f, g, (k, 0, 0, 1, cell / 2 - adv / 2 * k, 0), cell)
    asc, dsc = f["hhea"].ascent, f["hhea"].descent
    full = f["glyf"][cmap[0x2588]]; full.recalcBounds(f["glyf"])
    k = (asc - dsc) / (full.yMax - full.yMin)
    y0 = dsc - full.yMin * k
    for u in range(0x2580, 0x25A0):
        if u in cmap:
            redraw(f, cmap[u], (1, 0, 0, k, 0, y0), cell)
    f["post"].isFixedPitch = 1
    sort_features(f)
    f["OS/2"].recalcAvgCharWidth(f)

    n = f["name"]
    for r in list(n.names):
        if r.nameID >= 256 and r.toUnicode().strip() == "Paper":
            n.setName("a", r.nameID, r.platformID, r.platEncID, r.langID)
    nid = n.addMultilingualName({"en": "Text kerning"}, mac=False)
    for fr in f["GPOS"].table.FeatureList.FeatureRecord:
        if fr.FeatureTag == "ss20":
            fp = ot.FeatureParamsStylisticSet(); fp.Version = 0; fp.UINameID = nid
            fr.Feature.FeatureParams = fp
    f.save(p)
    leftovers = [r.toUnicode() for r in n.names if "paper" in r.toUnicode().lower() and r.nameID not in (0, 5, 9, 10)]
    print(p.split("/")[-1], "logo removed" if name else "no logo", "leftovers:", leftovers)
