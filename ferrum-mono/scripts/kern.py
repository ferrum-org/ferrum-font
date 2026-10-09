"""Optical pair kerning for Paper Mono Cyr, placed in stylistic set ss20
(off by default, so code and terminals keep the monospace grid).

For every pair the average white between the two glyphs is measured per
scanline (each side clamped DEPTH beyond the glyph's own extreme) and compared
with a reference pair of the same case (HH, Hn, nH, nn). The difference,
partially compensated, becomes the kern value."""
import sys, glob, io, json
import numpy as np
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

CAP, XH = 710, 509
STEP, DEPTH = 10, 80
FACTOR, MIN_KERN, MAX_NEG = 0.6, 20, -100
# Mono I i l j carry slab serifs: the white between the serifs is part of the
# letter, not room to kern into. Pairs with them get at most a light touch.
SERIFED, SERIF_MAX_NEG = set("IilјіІЈj"), -20
Y = np.arange(-190 + STEP / 2, 760, STEP)

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOWER = "abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
PUNCT = ".,:;!?«»"


def profiles(f, name):
    p = skPathFromGlyph(name, f.getGlyphSet())
    L = np.full(len(Y), np.nan); R = np.full(len(Y), np.nan)
    for i, y in enumerate(Y):
        band = pathops.Path()
        band.moveTo(-500, y - 1); band.lineTo(-500, y + 1); band.lineTo(1500, y + 1); band.lineTo(1500, y - 1); band.close()
        s = pathops.op(p, band, pathops.PathOp.INTERSECTION, fix_winding=True)
        if s.area > 0:
            b = s.bounds; L[i] = b[0]; R[i] = b[2]
    return L, R


def zone(ch):
    if ch in UPPER:
        return CAP
    return XH


class Kerner:
    def __init__(self, f):
        self.f = f; self.cmap = f.getBestCmap(); self.adv = f["hmtx"]["uni0410"][0]
        self.P = {}
        for ch in UPPER + LOWER + PUNCT:
            if ord(ch) in self.cmap:
                self.P[ch] = profiles(f, self.cmap[ord(ch)])

    def gap(self, a, b):
        La, Ra = self.P[a]; Lb, Rb = self.P[b]
        top = max(zone(a), zone(b))
        m = (Y >= 0) & (Y <= top)
        ext_a = np.nanmax(Ra); ext_b = np.nanmin(Lb)
        sa = np.where(np.isnan(Ra), self.adv - ext_a + DEPTH, np.minimum(self.adv - Ra, self.adv - ext_a + DEPTH))
        sb = np.where(np.isnan(Lb), ext_b + DEPTH, np.minimum(Lb, ext_b + DEPTH))
        both = ~np.isnan(Ra) & ~np.isnan(Lb)
        d = (self.adv - Ra) + Lb
        mind = np.nanmin(np.where(both, d, np.nan)) if both.any() else self.adv
        # only the concave white counts: the plain sidebearing of a narrow
        # mono glyph is deliberate and must not be kerned away
        conc = (sa - (self.adv - ext_a)) + (sb - ext_b)
        return float(np.mean(conc[m])), float(mind)

    def ref(self, a, b):
        ra = a if a in PUNCT else ("H" if a in UPPER else "n")
        rb = b if b in PUNCT else ("H" if b in UPPER else "n")
        return self.gap(ra, rb)

    def side_open(self, ch, side):
        """Concave white on one side, beyond what H / n have there."""
        L, R = self.P[ch]
        top = zone(ch)
        m = (Y >= 0) & (Y <= top)
        def conc(L, R, side):
            if side == "R":
                ext = np.nanmax(R); v = np.where(np.isnan(R), DEPTH, np.minimum(ext - R, DEPTH))
            else:
                ext = np.nanmin(L); v = np.where(np.isnan(L), DEPTH, np.minimum(L - ext, DEPTH))
            return float(np.mean(v[m]))
        refc = "H" if ch in UPPER else "n"
        return conc(L, R, side) - conc(*self.P[refc], side)

    def pairs(self):
        out = {}
        chars = list(self.P)
        for a in chars:
            for b in chars:
                if a in PUNCT and b in PUNCT:
                    continue
                if not (a in OPEN_R or b in OPEN_L):
                    continue
                g, mind = self.gap(a, b)
                r, rmin = self.ref(a, b)
                k = min((r - g) * FACTOR, 0)
                # tighten only while the ink stays clear of a near-collision
                k = max(k, -max(0.0, mind - 0.6 * rmin), MAX_NEG)
                if a in SERIFED or b in SERIFED:
                    k = max(k, SERIF_MAX_NEG)
                k = int(round(k / 5) * 5)
                if abs(k) >= MIN_KERN:
                    out[(a, b)] = k
        return out


# Glyphs whose RIGHT side is open (overhangs, diagonals, bowls low on the right)
OPEN_R = set("ГЃҐТTУЎYVWFРPLЬЪБКЖХKXАA«" + "гѓґтfrуўyvwрpьъкжхkx")
# Glyphs whose LEFT side is open
OPEN_L = set("АAДЛТTУYVWЧЪJХЖXЗЭОСQOCGЯ" + "аaлдтуyvwчъхжxзэосеёфcedgqoяj" + ".,:;!?»")


def graft(f, pairs):
    names = {ch: f.getBestCmap()[ord(ch)] for p in pairs for ch in p}
    lines = [f"    pos {names[a]} {names[b]} {k};" for (a, b), k in sorted(pairs.items())]
    fea = ("feature ss20 {\n    featureNames { name \"Text kerning\"; };\n    lookupflag 0;\n"
           + "\n".join(lines) + "\n} ss20;\n")
    buf = io.BytesIO(); f.save(buf); buf.seek(0); tmp = TTFont(buf)
    addOpenTypeFeaturesFromString(tmp, fea, tables=["GPOS"])
    orig, new = f["GPOS"].table, tmp["GPOS"].table
    off = len(orig.LookupList.Lookup)
    for lk in new.LookupList.Lookup:
        orig.LookupList.Lookup.append(lk)
    orig.LookupList.LookupCount = len(orig.LookupList.Lookup)
    for fr in new.FeatureList.FeatureRecord:
        if fr.FeatureTag == "ss20":
            fr.Feature.LookupListIndex = [i + off for i in fr.Feature.LookupListIndex]
            orig.FeatureList.FeatureRecord.append(fr)
    orig.FeatureList.FeatureCount = len(orig.FeatureList.FeatureRecord)
    fi = orig.FeatureList.FeatureCount - 1
    for sr in orig.ScriptList.ScriptRecord:
        lss = [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]
        for ls in lss:
            if ls is not None:
                ls.FeatureIndex.append(fi); ls.FeatureCount = len(ls.FeatureIndex)
    f["name"] = tmp["name"]


if __name__ == "__main__":
    report = {}
    for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
        f = TTFont(p)
        pairs = Kerner(f).pairs()
        graft(f, pairs)
        f.save(p)
        w = p.split("-")[-1][:-4]
        report[w] = {a + b: k for (a, b), k in pairs.items()}
        print(w, len(pairs), "pairs")
    json.dump(report, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
