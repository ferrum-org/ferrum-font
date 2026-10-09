"""Combining marks on Cyrillic (stress marks: за́мок, а́, И́).

- Cyrillic base letters join the top-mark attachment (GPOS mark): letters that
  are copies of Paper Latin glyphs take their twin's anchor, the others an
  anchor over the centre of the letter at x-height / cap height.
- Capitals switch the marks to their .case forms (ccmp), as Latin capitals do.
- і ј drop the dot before a top mark (ccmp), as i j do.
- U+02BC MODIFIER LETTER APOSTROPHE (Ukrainian apostrophe) maps to quoteright.
"""
import sys, glob, unicodedata
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.pens.recordingPen import DecomposingRecordingPen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def shape(f, name):
    p = DecomposingRecordingPen(f.getGlyphSet()); f.getGlyphSet()[name].draw(p); return repr(p.value)


def top_mark_lookup(gpos):
    """The MarkBasePos lookup that carries acutecomb."""
    for i in gpos.FeatureList.FeatureRecord:
        if i.FeatureTag != "mark":
            continue
        for li in i.Feature.LookupListIndex:
            st = gpos.LookupList.Lookup[li].SubTable[0]
            if type(st).__name__ == "MarkBasePos" and "acutecomb" in st.MarkCoverage.glyphs:
                return st


def anchor(x, y):
    a = ot.Anchor(); a.Format = 1; a.XCoordinate = round(x); a.YCoordinate = round(y); return a


def run(path):
    f = TTFont(path); cmap = f.getBestCmap(); glyf = f["glyf"]; order = f.getGlyphID
    st = top_mark_lookup(f["GPOS"].table)
    bases = dict(zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord))
    latin = {shape(f, n): n for n in bases if not n.startswith("uni04")}
    cap_y = bases["H"].BaseAnchor[0].YCoordinate
    x_y = bases["n"].BaseAnchor[0].YCoordinate
    asc_y = bases["b"].BaseAnchor[0].YCoordinate if "b" in bases else 747

    caps, added = [], 0
    for u, name in sorted(cmap.items()):
        if not (0x400 <= u < 0x530) or not unicodedata.category(chr(u)).startswith("L"):
            continue
        if chr(u).isupper():
            caps.append(name)
        if name in bases or unicodedata.decomposition(chr(u)):
            continue                       # already attached, or precomposed (ё й ї ...)
        twin = latin.get(shape(f, name))
        if twin:
            a = bases[twin].BaseAnchor[0]
            x, y = a.XCoordinate, a.YCoordinate
        else:
            g = glyf[name]; g.recalcBounds(glyf)
            x = (g.xMin + g.xMax) / 2
            y = cap_y if chr(u).isupper() else (asc_y if g.yMax > x_y + 100 else x_y)
        rec = ot.BaseRecord(); rec.BaseAnchor = [anchor(x, y)]
        bases[name] = rec; added += 1

    names = sorted(bases, key=order)
    st.BaseCoverage.glyphs = names
    st.BaseArray.BaseRecord = [bases[n] for n in names]
    st.BaseArray.BaseCount = len(names)

    # ccmp: capitals -> .case marks; і ј lose the dot before a top mark
    gsub = f["GSUB"].table
    for fr in gsub.FeatureList.FeatureRecord:
        if fr.FeatureTag != "ccmp":
            continue
        for li in fr.Feature.LookupListIndex:
            lk = gsub.LookupList.Lookup[li]
            for s in lk.SubTable:
                if lk.LookupType != 6 or s.Format != 3:
                    continue
                if s.BacktrackCoverage and "A" in s.BacktrackCoverage[0].glyphs:
                    cov = s.BacktrackCoverage[0]
                    cov.glyphs = sorted(set(cov.glyphs) | set(caps), key=order)
                if s.InputCoverage and set(s.InputCoverage[0].glyphs) == {"i", "j"}:
                    single = gsub.LookupList.Lookup[s.SubstLookupRecord[0].LookupListIndex].SubTable[0]
                    for cyr, lat in ((0x0456, "i"), (0x0458, "j")):
                        if cyr in cmap and lat in single.mapping:
                            single.mapping[cmap[cyr]] = single.mapping[lat]
                    s.InputCoverage[0].glyphs = sorted(set(s.InputCoverage[0].glyphs) | {cmap[c] for c in (0x0456, 0x0458) if c in cmap}, key=order)

    for t in f["cmap"].tables:
        if t.isUnicode() and 0x2019 in t.cmap:
            t.cmap[0x02BC] = t.cmap[0x2019]

    f.save(path)
    return added


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    print(p.replace("\\", "/").split("/")[-1], run(p), "Cyrillic bases anchored")
