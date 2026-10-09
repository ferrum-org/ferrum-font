"""Ferrum Mono as variable fonts (wght 100-800): upright and italic.

    python3 variable.py PAPER_VAR GEIST_VAR WORK ../fonts/variable

PAPER_VAR is Paper Mono's variable font (fonts/variable/PaperMono[wght].ttf),
GEIST_VAR the variable Geist Mono. One master per static weight is built with
the same steps as the static fonts, with two differences that keep the masters
point-compatible: the Latin comes from instances of Paper's variable font
(their outlines still overlap, where Paper's statics are merged), and fix.py /
redraw.py run with --variable (no outline cleanup; rebuilt letters kept as
overlapping parts). Kerning pairs are made the same in every master (0 where
a weight has none), then varLib builds the font. Paper's own feature variation
(Q with the bracketed tail from about wght 738 up) is carried over as rvrn.
The result is unhinted.

The italic is made from the same masters with oblique.py's shear and stroke
correction applied point by point (composites decomposed first, nothing
simplified), so the italic masters stay compatible too.
"""
import sys, os, glob, subprocess
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor, InstanceDescriptor
from fontTools import varLib
from fontTools.otlLib.builder import buildPairPosGlyphsSubtable, buildStatTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.varLib.featureVars import addFeatureVariations
import fontTools.subset  # noqa: F401  (adds prune_lookups to GSUB / GPOS)

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHTS = ["Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold"]
WGHT = dict(zip(WEIGHTS, range(100, 900, 100)))
FAMILY, PS = "Ferrum Mono", "FerrumMono"


def run(*args):
    subprocess.run([sys.executable, *args], cwd=HERE, check=True, stdout=subprocess.DEVNULL)


def masters(PAPER_VAR, GEIST_VAR, WORK):
    paper, out, ttf = (os.path.join(WORK, d) for d in ("paper", "out", "masters"))
    for d in (paper, out, ttf):
        os.makedirs(d, exist_ok=True)
        for f in glob.glob(os.path.join(d, "*.ttf")):
            os.remove(f)
    for w in WEIGHTS:
        f = instantiateVariableFont(TTFont(PAPER_VAR), {"wght": WGHT[w]}, updateFontNames=False)
        for t in ("prep", "fpgm", "cvt ", "STAT", "avar", "meta"):
            if t in f:
                del f[t]
        drop_rvrn(f)
        f.save(os.path.join(paper, f"PaperMono-{w}.ttf"))
    run("build.py", paper, GEIST_VAR, out)
    run("fix.py", out, "--variable")
    run("redraw.py", out, "--variable")
    run("respace.py", out, ".")
    run("kern.py", out, os.path.join(WORK, "pairs.json"))
    run("addcyrl.py", out)
    run("marks.py", out)
    run("locl.py", out, "--variable")
    run("symbols.py", out, "--variable")
    run("arch.py", out)
    run("chisel.py", out, "--variable")
    run("contrast.py", out, "--variable")
    run("rename.py", out, ttf)
    run("clean.py", ttf)
    return ttf


def drop_rvrn(f):
    """Instances keep Paper's rvrn only where its condition holds; the masters
    must agree, so it goes (with its lookups), and comes back as a feature
    variation of the finished font."""
    if True:
        t = f["GSUB"].table
        keep = [i for i, r in enumerate(t.FeatureList.FeatureRecord) if r.FeatureTag != "rvrn"]
        new = {old: i for i, old in enumerate(keep)}
        t.FeatureList.FeatureRecord = [t.FeatureList.FeatureRecord[i] for i in keep]
        t.FeatureList.FeatureCount = len(keep)
        for sr in t.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is not None:
                    ls.FeatureIndex = [new[i] for i in ls.FeatureIndex if i in new]
                    ls.FeatureCount = len(ls.FeatureIndex)
        f["GSUB"].prune_lookups()


def paper_variations(PAPER_VAR):
    """Paper's rvrn condition, moved from its avar-mapped axis to ours (none)."""
    f = TTFont(PAPER_VAR)
    seg = f["avar"].segments["wght"] if "avar" in f else {-1: -1, 0: 0, 1: 1}
    ax = f["fvar"].axes[0]
    out = []
    for rec in f["GSUB"].table.FeatureVariations.FeatureVariationRecord:
        c = rec.ConditionSet.ConditionTable[0]
        lo = c.FilterRangeMinValue
        # invert Paper's avar (piecewise linear) to user space
        pts = sorted(seg.items())
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if b0 <= lo <= b1:
                n = a0 + (lo - b0) * (a1 - a0) / (b1 - b0)
                break
        user = ax.defaultValue + n * ((ax.maxValue - ax.defaultValue) if n > 0 else (ax.defaultValue - ax.minValue))
        ours = (user - 400) / 400
        subs = {}
        for sr in rec.FeatureTableSubstitution.SubstitutionRecord:
            for li in sr.Feature.LookupListIndex:
                for st in f["GSUB"].table.LookupList.Lookup[li].SubTable:
                    subs.update(st.mapping)
        out.append(([{"wght": (ours, 1.0)}], subs))
    return out


def same_kerning(paths, tag="ss20"):
    """One pair list for every master: varLib merges pair values per pair."""
    fonts = {p: TTFont(p) for p in paths}

    def ss20(f):
        g = f["GPOS"].table
        idx = next(r.Feature.LookupListIndex for r in g.FeatureList.FeatureRecord if r.FeatureTag == tag)
        return [g.LookupList.Lookup[i] for i in idx]

    pairs = {}
    for p, f in fonts.items():
        d = {}
        for lk in ss20(f):
            for st in lk.SubTable:
                for first, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for r in ps.PairValueRecord:
                        d[(first, r.SecondGlyph)] = r.Value1.XAdvance
        pairs[p] = d
    every = sorted(set().union(*pairs.values()))
    for p, f in fonts.items():
        vals = {}
        for k in every:
            v = ot.ValueRecord(); v.XAdvance = pairs[p].get(k, 0)
            vals[k] = (v, None)
        lk = ss20(f)[0]
        lk.SubTable = [buildPairPosGlyphsSubtable(vals, f.getReverseGlyphMap())]
        lk.SubTableCount = 1
        f.save(p)
    return len(every)


_ob = os.path.join(HERE, "oblique.py")
_obsrc = open(_ob, encoding="utf-8").read()
OB = {}
exec(compile(_obsrc[:_obsrc.index("\nfor p in sorted(glob.glob(os.path.join(sys.argv[1]")], _ob, "exec"), OB)


def italic_masters(src_dir, dst_dir):
    """oblique.py's slant on every master, point by point."""
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
    from fontTools.ttLib.tables import ttProgram
    os.makedirs(dst_dir, exist_ok=True)
    for f_ in glob.glob(os.path.join(dst_dir, "*.ttf")):
        os.remove(f_)
    for src in sorted(glob.glob(os.path.join(src_dir, "*.ttf"))):
        f = TTFont(src); glyf = f["glyf"]
        keep = OB["upright_glyphs"](f)
        cmap = f.getBestCmap()

        gs = f.getGlyphSet()
        sk = OB["skPathFromGlyph"]
        n_stem = (lambda r: r[0][1] - r[0][0])(OB["runs"](sk(cmap[ord("n")], gs), 200))
        H_stem = (lambda r: r[0][1] - r[0][0])(OB["runs"](sk(cmap[ord("H")], gs), 200))
        # composites stay composites (a shear is linear: the parts are slanted
        # and each offset (dx, dy) becomes (dx + dy * tan, dy)); only those that
        # stay upright, or are built from parts that stay upright, are
        # decomposed from the upright points first
        def mixes(name, seen=()):
            g = glyf[name]
            return g.isComposite() and any(c.glyphName in keep or mixes(c.glyphName) for c in g.components)
        flat = {}
        for name in f.getGlyphOrder():
            g = glyf[name]
            if g.isComposite() and (name in keep or mixes(name)):
                flat[name] = g.getCoordinates(glyf)
        for name, (c, e, fl) in flat.items():
            g = Glyph(); g.numberOfContours = len(e); g.endPtsOfContours = list(e)
            g.coordinates = GlyphCoordinates(list(c)); g.flags = bytearray(x & 1 for x in fl)
            g.program = ttProgram.Program(); g.program.fromBytecode(b"")
            glyf[name] = g
        for name in f.getGlyphOrder():
            g = glyf[name]
            if g.isComposite():
                if name not in keep:
                    for c in g.components:
                        c.x = round(c.x + c.y * OB["TAN"])
                    g.recalcBounds(glyf)
                    f["hmtx"][name] = (f["hmtx"][name][0], getattr(g, "xMin", 0))
                continue
            if name in keep or g.numberOfContours <= 0:
                continue
            g.coordinates = type(g.coordinates)([(OB["shear_x"](x, y), y) for x, y in g.coordinates])
            g.recalcBounds(glyf)
            OB["compensate"](g, H_stem if getattr(g, "yMax", 0) > OB["XH"] + 60 else n_stem)
            g.recalcBounds(glyf)
            f["hmtx"][name] = (f["hmtx"][name][0], getattr(g, "xMin", 0))
        for lk in f["GPOS"].table.LookupList.Lookup:
            for st in lk.SubTable:
                kind = type(st).__name__
                anchors = []
                if kind == "MarkBasePos":
                    anchors += [a for r in st.BaseArray.BaseRecord for a in r.BaseAnchor]
                    anchors += [r.MarkAnchor for r in st.MarkArray.MarkRecord]
                elif kind == "MarkMarkPos":
                    anchors += [a for r in st.Mark2Array.Mark2Record for a in r.Mark2Anchor]
                    anchors += [r.MarkAnchor for r in st.Mark1Array.MarkRecord]
                for a in anchors:
                    if a is not None:
                        a.XCoordinate = round(OB["shear_x"](a.XCoordinate, a.YCoordinate))
        italic_metadata(f)
        f.save(os.path.join(dst_dir, os.path.basename(src)))
    return dst_dir


def italic_metadata(f):
    f["post"].italicAngle = -OB["ANGLE"]
    f["hhea"].caretSlopeRise = 1000
    f["hhea"].caretSlopeRun = round(1000 * OB["TAN"])
    f["hhea"].caretOffset = 0
    f["OS/2"].fsSelection = (f["OS/2"].fsSelection | 1) & ~(1 << 6) & ~(1 << 5)
    f["head"].macStyle = (f["head"].macStyle | 2) & ~1


def build(ttf_dir, PAPER_VAR, FAMILY=FAMILY, PS=PS, italic=False):
    ds = DesignSpaceDocument()
    a = AxisDescriptor(); a.tag = "wght"; a.name = "Weight"; a.minimum, a.default, a.maximum = 100, 400, 800
    ds.addAxis(a)
    for w in WEIGHTS:
        s = SourceDescriptor(); s.path = os.path.join(ttf_dir, f"{PS}-{w}.ttf"); s.location = {"Weight": WGHT[w]}
        s.styleName = w
        ds.addSource(s)
        style = (("Italic" if w == "Regular" else f"{w} Italic") if italic else w)
        i = InstanceDescriptor(); i.styleName = style; i.familyName = FAMILY; i.location = {"Weight": WGHT[w]}
        i.postScriptFontName = f"{PS}-" + style.replace(" ", "")
        ds.addInstance(i)
    vf, _, _ = varLib.build(ds)
    addFeatureVariations(vf, paper_variations(PAPER_VAR), featureTag="rvrn")

    # names: family / default style, variations PostScript prefix
    n = vf["name"]
    for r in list(n.names):
        if r.nameID in (16, 17):
            n.removeNames(nameID=r.nameID)
    sub = "Italic" if italic else "Regular"
    n.setName(FAMILY, 1, 3, 1, 0x409); n.setName(sub, 2, 3, 1, 0x409)
    n.setName(f"{FAMILY} {sub}", 4, 3, 1, 0x409); n.setName(f"{PS}-{sub}", 6, 3, 1, 0x409)
    n.setName(PS + ("Italic" if italic else ""), 25, 3, 1, 0x409)
    ital = (dict(value=1, name="Italic") if italic
            else dict(value=0, name="Roman", flags=0x2, linkedValue=1))
    buildStatTable(vf, [
        dict(tag="wght", name="Weight", values=[
            dict(value=WGHT[w], name=w, **({"flags": 0x2, "linkedValue": 700} if w == "Regular" else {}))
            for w in WEIGHTS]),
        dict(tag="ital", name="Italic", values=[ital])], elidedFallbackName=2)
    vf["OS/2"].usWeightClass = 400
    if italic:
        italic_metadata(vf)
    else:
        vf["OS/2"].fsSelection = (vf["OS/2"].fsSelection | (1 << 6)) & ~1 & ~(1 << 5)
        vf["head"].macStyle &= ~3
    n.removeNames(platformID=1)                       # Windows records only, as in the statics
    # unhinted: smooth at every size, and smart dropout control in prep
    # (PUSHW 511, SCANCTRL, PUSHB 4, SCANTYPE)
    if "gasp" not in vf:
        vf["gasp"] = newTable("gasp"); vf["gasp"].version = 1
    vf["gasp"].gaspRange = {0xFFFF: 0x000F}
    prep = newTable("prep"); prep.program = ttProgram.Program()
    prep.program.fromBytecode(bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D]))
    vf["prep"] = prep
    return vf


def save(vf, out_dir, ps, italic=False):
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{ps}{'-Italic' if italic else ''}[wght].ttf")
    vf.save(out)
    vf.flavor = "woff2"; vf.save(out[:-4] + ".woff2")
    return out


if __name__ == "__main__":
    PAPER_VAR, GEIST_VAR, WORK, OUT = sys.argv[1:5]
    ttf = masters(PAPER_VAR, GEIST_VAR, WORK)
    n = same_kerning(sorted(glob.glob(os.path.join(ttf, "*.ttf"))))
    for italic in (False, True):
        src = italic_masters(ttf, os.path.join(WORK, "masters-italic")) if italic else ttf
        vf = build(src, PAPER_VAR, italic=italic)
        out = save(vf, OUT, PS, italic)
        print(out, os.path.getsize(out) // 1024, "KB;", os.path.getsize(out[:-4] + ".woff2") // 1024, "KB woff2;", n, "kerning pairs")
