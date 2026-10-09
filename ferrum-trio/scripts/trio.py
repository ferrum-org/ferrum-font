"""Ferrum Trio from Ferrum Mono: the same letters on a grid of three widths.

    0.5 cell   space, I i l and their accented forms, І і Ї ї, . , : ; ! | ' ’
    1 cell     everything else (digits stay tabular)
    1.5 cell   М Ш Щ Ю Ж Ы Љ Њ, M W Æ Œ and their lowercase (+ accented forms)

Narrow letters: the serifs are trimmed to the half cell around the stem;
accents and dots are only moved (the i dot optically, against the flag).
Wide letters: stretched horizontally, then every vertical edge is pulled back
by the stroke's own share of the stretch, so stems, bowls and diagonals keep
their thickness; the three-stem letters get back the full stem weight the
mono cell took from them. Ж ж Җ җ are drawn anew for the wide cell (full-weight
stem, the same stepped join). Kerning (Mono's ss20) is on by default as 'kern'.

Extras: small caps (smcp, c2sc) from Mono's capitals, scaled to SC_H with the
stems brought to the lowercase weight, one cell wide (half for I); a
proportional 1 (pnum) on the half cell. Bulgarian locl forms follow their base
widths (ɯ-shaped ш щ wide like ш, т -> m wide, п -> n one cell).

    python3 trio.py ../../ferrum-mono/fonts/ttf ../fonts/ttf

With --variable (masters of the variable font, built from Ferrum Mono's
variable masters) outlines are kept as overlapping parts and every weight
keeps the same point structure.
"""
import sys, os, glob, unicodedata
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph, ttfGlyphFromSkPath
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools import subset

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC, DST = sys.argv[1], sys.argv[2]
VARIABLE = "--variable" in sys.argv[3:]
CELL = 606
HALF, WIDE = CELL // 2, CELL * 3 // 2           # 303, 909
NARROW_SB = 40                                   # side space of the narrow letters
WIDE_BODY = 200                                  # of the extra half cell, this much goes into the letter
CAP, XH, ASC = 710, 509, 747
VERSION = "1.003"

NARROW_BASES = {"I": CAP, "i": XH, "ı": XH, "l": ASC, "І": CAP, "і": XH}
NARROW_PUNCT = "  .,:;!|'’‘‚·"
NARROW_SKIP = set("ľŀĿ")                         # their mark sits beside the stem
WIDE_BASES = {c: CAP for c in "MWÆŒМШЩЮЖЫЉЊҖ"} | {c: XH for c in "mwæœмшщюжыљњҗ"}
REWEIGHT = set("mMМшщыШЩЫ")                      # thinned to fit the mono cell
ZHE = {"Ж": CAP, "ж": XH, "Җ": CAP, "җ": XH}      # drawn anew, see zhe()
ZHE_STEP, ZHE_STEP_WIDE = 0.30, 0.55              # step gap x stem; cv02 = wide
I_DOT = set("iıі")                                 # dots / accents set against the flag
SC_H = round(XH * 1.06)                            # small-cap height

# Ferrum Mono's drawing helpers (rect, diag, U, I, moved, slice_spans ...)
_rd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ferrum-mono", "scripts", "redraw.py")
_src = open(_rd, encoding="utf-8").read()
RD = {}
exec(compile(_src[:_src.index("\nfor p in sorted(glob.glob")], _rd, "exec"), RD)
RD["VARIABLE"] = VARIABLE


def base_char(ch):
    """The letter an accented letter is built on (í -> i, Ӂ -> Ж)."""
    d = unicodedata.decomposition(ch)
    while d and not d.startswith("<"):
        ch = chr(int(d.split()[0], 16))
        d = unicodedata.decomposition(ch)
    return ch


def rect(x0, y0, x1, y1):
    p = pathops.Path(); p.moveTo(x0, y0); p.lineTo(x0, y1); p.lineTo(x1, y1); p.lineTo(x1, y0); p.close()
    return p


def op(a, b, kind):
    if VARIABLE and kind == pathops.PathOp.UNION:
        return RD["U"](a, b)                       # overlapping parts, not merged
    if VARIABLE and kind == pathops.PathOp.INTERSECTION:
        return RD["I"](a, b)                       # uncrossed contours untouched
    return pathops.op(a, b, kind, fix_winding=True)


def runs(path, y):
    path = RD["merged"](path)
    s = pathops.op(path, rect(-2000, y - 0.5, 3000, y + 0.5), pathops.PathOp.INTERSECTION, fix_winding=True)
    return sorted((c.bounds[0], c.bounds[2]) for c in s.contours)


def transformed(path, fx):
    """path with every point's x mapped through fx."""
    if isinstance(path, list):
        return [transformed(p, fx) for p in path]
    out = pathops.Path(); pen = out.getPen()

    class T:
        def moveTo(self, p): pen.moveTo((fx(p[0]), p[1]))
        def lineTo(self, p): pen.lineTo((fx(p[0]), p[1]))
        def qCurveTo(self, *ps): pen.qCurveTo(*[None if p is None else (fx(p[0]), p[1]) for p in ps])
        def curveTo(self, *ps): pen.curveTo(*[(fx(x), y) for x, y in ps])
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    path.draw(T())
    return out


def local_strokes(glyph, p_ref):
    """Per edge, the thickness of the stroke it bounds: from the edge's middle
    straight inwards to the first other edge. Strokes of one letter differ
    (W's outer diagonals are heavier than the inner ones); one p_ref for all
    would thin the light ones. Falls back to p_ref where the ray finds no
    sensible opposite side (counters wider than a stroke, open ends)."""
    import math
    pts = [tuple(map(float, q)) for q in glyph.coordinates]
    segs, start = [], 0
    for end in glyph.endPtsOfContours:
        n = end - start + 1
        segs += [(start + i, pts[start + i], pts[start + (i + 1) % n]) for i in range(n)]
        start = end + 1
    out = {}
    for i, a, b in segs:
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        if L < 1e-6:
            continue
        nx, ny = ty / L, -tx / L                   # inward for a clockwise contour
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        best = None
        for j, c, d in segs:
            if j == i:
                continue
            ex, ey = d[0] - c[0], d[1] - c[1]
            den = nx * ey - ny * ex
            if abs(den) < 1e-9:
                continue
            t = ((c[0] - mx) * ey - (c[1] - my) * ex) / den
            u = ((c[0] - mx) * ny - (c[1] - my) * nx) / den
            if t > 1 and 0 <= u <= 1 and (best is None or t < best):
                best = t
        out[i] = best if best is not None and 0.5 * p_ref < best < 1.5 * p_ref else p_ref
    return out


def compensate(glyph, k, p_ref, extra=0.0, local=None):
    """After a horizontal stretch by k, move every edge along its normal so a
    stroke of perpendicular thickness p_ref gets that thickness back, whatever
    its slope (vertical edges: (k-1)*p/2 each; horizontal edges: untouched).
    `extra` adds stroke weight (perpendicular) on the near-vertical edges.
    Vertices go to the intersection of their two moved edges."""
    import math
    pts = [tuple(map(float, q)) for q in glyph.coordinates]
    out = list(pts); start = 0

    def edge(a, b, idx=None):
        p = local.get(idx, p_ref) if local is not None else p_ref
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        if L < 1e-6:
            return None
        n = (-ty / L, tx / L)                      # outward for a clockwise contour
        sp = abs(n[0])                             # sin of the edge's angle to the horizontal
        if sp < 1e-3:
            return n, 0.0
        if sp > 0.9999:
            q = p / 2 * (1 - k)
        else:
            tp = sp / math.sqrt(1 - sp * sp)
            sth = k * tp / math.hypot(1, k * tp)   # the angle before the stretch
            q = p / 2 * (1 - k * sp / sth)
        if local is not None:
            # per-stroke thickness: the extra weight is for the stems only
            # (diagonals keep their own, lighter weight)
            return n, q + (extra / 2 if sp > 0.99 else 0.0)
        return n, q + extra / 2 * sp

    for end in glyph.endPtsOfContours:
        n_pts = end - start + 1
        for i in range(n_pts):
            a, b, c = pts[start + (i - 1) % n_pts], pts[start + i], pts[start + (i + 1) % n_pts]
            e1, e2 = edge(a, b, start + (i - 1) % n_pts), edge(b, c, start + i)
            if e1 is None and e2 is None:
                continue
            if e1 is None or e2 is None:
                (n, q) = e1 or e2
                out[start + i] = (b[0] + n[0] * q, b[1] + n[1] * q)
                continue
            (n1, q1), (n2, q2) = e1, e2
            det = n1[0] * n2[1] - n1[1] * n2[0]
            if abs(det) < 0.05:                    # nearly collinear: plain offset
                n = ((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2); q = (q1 + q2) / 2
                out[start + i] = (b[0] + n[0] * q, b[1] + n[1] * q)
                continue
            # solve n1.(p-b) = q1, n2.(p-b) = q2
            dx = (q1 * n2[1] - q2 * n1[1]) / det
            dy = (n1[0] * q2 - n2[0] * q1) / det
            lim = 3 * max(abs(q1), abs(q2), 1)
            if math.hypot(dx, dy) > lim:            # spike guard on sharp joins
                f = lim / math.hypot(dx, dy); dx, dy = dx * f, dy * f
            out[start + i] = (b[0] + dx, b[1] + dy)
        start = end + 1
    glyph.coordinates = type(glyph.coordinates)([(round(x), round(y)) for x, y in out])


def offset_edges(glyph, qfun):
    """Move every edge along its outward normal by qfun(normal); vertices go to
    the intersection of their two moved edges (spikes on sharp joins capped)."""
    import math
    pts = [tuple(map(float, q)) for q in glyph.coordinates]
    out = list(pts); start = 0

    def edge(a, b):
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        if L < 1e-6:
            return None
        n = (-ty / L, tx / L)
        return n, qfun(n)

    for end in glyph.endPtsOfContours:
        n_pts = end - start + 1
        for i in range(n_pts):
            a, b, c = pts[start + (i - 1) % n_pts], pts[start + i], pts[start + (i + 1) % n_pts]
            e1, e2 = edge(a, b), edge(b, c)
            if e1 is None and e2 is None:
                continue
            if e1 is None or e2 is None:
                n, q = e1 or e2
                out[start + i] = (b[0] + n[0] * q, b[1] + n[1] * q)
                continue
            (n1, q1), (n2, q2) = e1, e2
            det = n1[0] * n2[1] - n1[1] * n2[0]
            if abs(det) < 0.05:
                n = ((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2); q = (q1 + q2) / 2
                out[start + i] = (b[0] + n[0] * q, b[1] + n[1] * q)
                continue
            dx = (q1 * n2[1] - q2 * n1[1]) / det
            dy = (n1[0] * q2 - n2[0] * q1) / det
            lim = 3 * max(abs(q1), abs(q2), 1)
            if math.hypot(dx, dy) > lim:
                k = lim / math.hypot(dx, dy); dx, dy = dx * k, dy * k
            out[start + i] = (b[0] + dx, b[1] + dy)
        start = end + 1
    glyph.coordinates = type(glyph.coordinates)([(round(x), round(y)) for x, y in out])


def transformed_xy(path, fxy):
    out = pathops.Path(); pen = out.getPen()

    class T:
        def moveTo(self, p): pen.moveTo(fxy(*p))
        def lineTo(self, p): pen.lineTo(fxy(*p))
        def qCurveTo(self, *ps): pen.qCurveTo(*[None if p is None else fxy(*p) for p in ps])
        def curveTo(self, *ps): pen.curveTo(*[fxy(*p) for p in ps])
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    path.draw(T())
    return out


def add_glyph(f, name, path, adv):
    if name not in f["glyf"]:
        f.setGlyphOrder(f.getGlyphOrder() + [name])
    put(f, name, path, adv)
    return name


def add_single_feature(f, tag, mapping, first=False):
    """A SingleSubst lookup under a new `tag` feature in every language system.
    first=True puts the lookup ahead of all others (so smcp sees the letters
    before locl turns, say, Bulgarian т into m)."""
    from fontTools.ttLib.tables import otTables as ot
    gsub = f["GSUB"].table
    lk = ot.Lookup(); lk.LookupType = 1; lk.LookupFlag = 0
    st = ot.SingleSubst(); st.mapping = dict(mapping); lk.SubTable = [st]; lk.SubTableCount = 1
    if first:
        def bump(lookup):
            for sub in lookup.SubTable:
                sub = getattr(sub, "ExtSubTable", sub)
                for attr in ("SubstLookupRecord",):
                    for r in getattr(sub, attr, None) or []:
                        r.LookupListIndex += 1
                for rs_attr in ("SubRuleSet", "ChainSubRuleSet", "SubClassSet", "ChainSubClassSet"):
                    for rs in getattr(sub, rs_attr, None) or []:
                        if rs is None:
                            continue
                        for rule in (getattr(rs, "SubRule", None) or getattr(rs, "ChainSubRule", None)
                                     or getattr(rs, "SubClassRule", None) or getattr(rs, "ChainSubClassRule", None) or []):
                            for r in rule.SubstLookupRecord:
                                r.LookupListIndex += 1
        for old in gsub.LookupList.Lookup:
            bump(old)
        for fr in gsub.FeatureList.FeatureRecord:
            fr.Feature.LookupListIndex = [i + 1 for i in fr.Feature.LookupListIndex]
        gsub.LookupList.Lookup.insert(0, lk)
        idx = 0
    else:
        gsub.LookupList.Lookup.append(lk); idx = len(gsub.LookupList.Lookup) - 1
    gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
    fr = ot.FeatureRecord(); fr.FeatureTag = tag
    fr.Feature = ot.Feature(); fr.Feature.FeatureParams = None
    fr.Feature.LookupListIndex = [idx]; fr.Feature.LookupCount = 1
    gsub.FeatureList.FeatureRecord.append(fr); gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    fi = gsub.FeatureList.FeatureCount - 1
    for sr in gsub.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex.append(fi); ls.FeatureCount = len(ls.FeatureIndex)


def stroke_at(path, y, dy=20):
    """Perpendicular thickness of the leftmost stroke crossing height y."""
    import math
    a, b = runs(path, y), runs(path, y + dy)
    if not a:
        return None
    w = a[0][1] - a[0][0]
    if len(a) == len(b):
        slope = ((b[0][0] + b[0][1]) / 2 - (a[0][0] + a[0][1]) / 2) / dy
        return w / math.hypot(1, slope)
    return w


def drop_tiny(glyph, eps=1.5):
    """Remove points closer than eps to the previous kept point of their contour."""
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    if glyph.numberOfContours <= 0:
        return glyph
    coords, flags, ends = list(glyph.coordinates), list(glyph.flags), glyph.endPtsOfContours
    nc, nf, ne, start = [], [], [], 0
    for end in ends:
        kept = []
        for i in range(start, end + 1):
            if kept and abs(coords[i][0] - coords[kept[-1]][0]) + abs(coords[i][1] - coords[kept[-1]][1]) < eps:
                if flags[i] & 1:
                    kept[-1] = i            # keep the on-curve one
                continue
            kept.append(i)
        if len(kept) > 1 and abs(coords[kept[0]][0] - coords[kept[-1]][0]) + abs(coords[kept[0]][1] - coords[kept[-1]][1]) < eps:
            kept.pop()
        if len(kept) >= 3:
            nc += [coords[i] for i in kept]; nf += [flags[i] for i in kept]; ne.append(len(nc) - 1)
        start = end + 1
    glyph.coordinates = GlyphCoordinates(nc); glyph.flags = bytearray(nf); glyph.endPtsOfContours = ne
    glyph.numberOfContours = len(ne)
    return glyph


def put(f, name, path, adv):
    if VARIABLE:
        g = RD["ttglyph"](path)
    else:
        path = pathops.simplify(path, fix_winding=True, clockwise=True)
        g = ttfGlyphFromSkPath(path)
        # rounding to the unit grid can leave zero-length bits: clean once more
        again = pathops.Path(); g.draw(again.getPen(), None)
        g = drop_tiny(ttfGlyphFromSkPath(pathops.simplify(again, fix_winding=True, clockwise=True)))
        last = pathops.Path(); g.draw(last.getPen(), None)
        g = ttfGlyphFromSkPath(pathops.simplify(last, fix_winding=True, clockwise=True))
    f["glyf"][name] = g
    g.recalcBounds(f["glyf"])
    f["hmtx"][name] = (adv, getattr(g, "xMin", 0))


def split_tt(tt, above):
    """(coords, ends, flags) -> glyph of the contours below `above` and glyph
    of the contours wholly above it (accents)."""
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
    coords, ends, flags = tt
    parts = ([], [])
    start = 0
    for e in ends:
        c = [(tuple(coords[i]), flags[i] & 1) for i in range(start, e + 1)]
        parts[1 if min(pt[1] for pt, _ in c) > above else 0].append(c)
        start = e + 1
    out = []
    for cs in parts:
        if not cs:
            out.append(None); continue
        g = Glyph(); pts, fl, en = [], [], []
        for c in cs:
            pts += [pt for pt, _ in c]; fl += [o for _, o in c]; en.append(len(pts) - 1)
        g.numberOfContours = len(en); g.endPtsOfContours = en
        g.coordinates = GlyphCoordinates(pts); g.flags = bytearray(fl)
        from fontTools.ttLib.tables import ttProgram
        g.program = ttProgram.Program(); g.program.fromBytecode(b"")
        out.append(g)
    return out[0], out[1]


def put_glyph(f, name, g, extra, adv):
    """A glyph from ready TrueType contours (variable masters)."""
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
    pts, flags, ends = list(g.coordinates), list(g.flags), list(g.endPtsOfContours)
    if extra is not None and extra.numberOfContours > 0:
        off = len(pts)
        pts += list(extra.coordinates); flags += list(extra.flags)
        ends += [e + off for e in extra.endPtsOfContours]
    out = Glyph(); out.numberOfContours = len(ends); out.endPtsOfContours = ends
    out.coordinates = GlyphCoordinates([(round(x), round(y)) for x, y in pts])
    out.flags = bytearray(x & 1 for x in flags); out.program = g.program
    f["glyf"][name] = out
    out.recalcBounds(f["glyf"])
    f["hmtx"][name] = (adv, getattr(out, "xMin", 0))


def glyph_path(f, name):
    return skPathFromGlyph(name, f.getGlyphSet())


def move_anchors(f, moves):
    """Base anchors of re-widthed glyphs follow the outline."""
    gpos = f["GPOS"].table
    for lk in gpos.LookupList.Lookup:
        for st in lk.SubTable:
            if type(st).__name__ != "MarkBasePos":
                continue
            for name, rec in zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord):
                if name in moves:
                    for a in rec.BaseAnchor:
                        if a is not None:
                            a.XCoordinate = round(moves[name](a.XCoordinate))


def sort_features(f):
    for tag in ("GSUB", "GPOS"):
        t = f[tag].table
        recs = t.FeatureList.FeatureRecord
        order = sorted(range(len(recs)), key=lambda i: recs[i].FeatureTag)
        new = {old: i for i, old in enumerate(order)}
        t.FeatureList.FeatureRecord = [recs[i] for i in order]
        t.FeatureList.FeatureCount = len(recs)
        for sr in t.ScriptList.ScriptRecord:
            for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
                if ls is not None:
                    ls.FeatureIndex = sorted(new[i] for i in ls.FeatureIndex)


def drop_features(f, table, tags):
    t = f[table].table
    keep = [i for i, r in enumerate(t.FeatureList.FeatureRecord) if r.FeatureTag not in tags]
    new = {old: i for i, old in enumerate(keep)}
    t.FeatureList.FeatureRecord = [t.FeatureList.FeatureRecord[i] for i in keep]
    t.FeatureList.FeatureCount = len(keep)
    for sr in t.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex = [new[i] for i in ls.FeatureIndex if i in new]


def unhinted(src):
    """Mono's fonts are already autohinted: drop the hints and ttfautohint's
    marker glyph so hint.py can hint the new outlines from scratch."""
    f = TTFont(src)
    o = subset.Options()
    o.hinting = False; o.layout_features = ["*"]; o.name_IDs = ["*"]; o.name_languages = ["*"]
    o.name_legacy = True; o.glyph_names = True; o.notdef_outline = True; o.legacy_kern = True
    o.drop_tables = []; o.passthrough_tables = True; o.recalc_bounds = True
    s = subset.Subsetter(o)
    s.populate(glyphs=[g for g in f.getGlyphOrder() if g != ".ttfautohint"], unicodes=f.getBestCmap().keys())
    s.subset(f)
    return f


def build(src, dst):
    f = unhinted(src)
    cmap = f.getBestCmap()
    order = f.getGlyphOrder()
    rev = {}
    for u, n in cmap.items():
        rev.setdefault(n, u)
    moves = {}

    def stem(ch, y):
        r = runs(glyph_path(f, cmap[ord(ch)]), y)
        return r[0][1] - r[0][0]
    n_stem, H_stem = stem("n", 200), stem("H", 200)

    # group glyphs by what they are built on; alternates follow their base name
    narrow, wide = {}, {}
    for name in order:
        u = rev.get(name) or rev.get(name.split(".")[0])
        if u is None:
            continue
        ch = chr(u)
        if ch in NARROW_SKIP:
            continue
        b = base_char(ch)
        if ch in NARROW_PUNCT:
            narrow[name] = None
        elif b in NARROW_BASES:
            narrow[name] = NARROW_BASES[b]
        elif b in WIDE_BASES:
            top = WIDE_BASES[b]
            if name.endswith(".loclBGR") and b == "ю":
                top = ASC                                   # the stem rises to the ascender
            wide[name] = (top, b)
    for name in ("dotlessi", "i.loclTRK"):
        if name in f["glyf"]:
            narrow[name] = XH

    # every outline is taken before anything changes; composites that are not
    # re-widthed themselves but use a re-widthed glyph are frozen as outlines
    changed = set(narrow) | set(wide)
    orig = {name: glyph_path(f, name) for name in changed}
    # the same outlines as TrueType points (decomposed), for the variable masters
    orig_tt = {name: f["glyf"][name].getCoordinates(f["glyf"]) for name in changed} if VARIABLE else {}
    glyf = f["glyf"]

    def uses(name, seen=()):
        g = glyf[name]
        if not g.isComposite():
            return False
        return any(c.glyphName in changed or uses(c.glyphName) for c in g.components)
    for name in order:
        if name not in changed and glyf[name].isComposite() and uses(name):
            adv = f["hmtx"][name][0]
            put(f, name, glyph_path(f, name), adv)

    # --- narrow ------------------------------------------------------------
    hw = HALF / 2 - NARROW_SB
    for name, top in narrow.items():
        p = orig[name]
        if p.bounds == (0, 0, 0, 0):                        # spaces
            f["glyf"][name] = f["glyf"][name]; f["hmtx"][name] = (HALF, 0)
            moves[name] = lambda x: x - CELL / 2 + HALF / 2
            continue
        if top is None:                                     # punctuation: centre it
            cx = (p.bounds[0] + p.bounds[2]) / 2
            base, acc = p, pathops.Path()
        else:
            base = op(p, rect(-2000, -1000, 3000, top + 5), pathops.PathOp.INTERSECTION)
            acc = op(p, rect(-2000, top + 5, 3000, 2000), pathops.PathOp.INTERSECTION)
            r = runs(base, top * 0.45)
            cx = (r[0][0] + r[0][1]) / 2 if r else (p.bounds[0] + p.bounds[2]) / 2
            # ogonek / comma below the baseline: moved with the letter, never
            # trimmed by the half cell (only pulled in if it would stick out)
            below = pathops.Path()
            if VARIABLE:
                # an overlapping contour of its own in the variable masters
                body = pathops.Path()
                for c in base.contours:
                    x0, y0, x1, y1 = c.bounds
                    c.draw((below if y0 < -20 and y1 < top * 0.3 else body).getPen())
                base = body
            else:
                below = pathops.op(base, rect(-2000, -1000, 3000, 0), pathops.PathOp.INTERSECTION, fix_winding=True)
                if below.bounds[1] > -20:
                    below = pathops.Path()           # only serif feet down there, nothing hanging
                else:
                    base = pathops.op(base, rect(-2000, 0, 3000, 2000), pathops.PathOp.INTERSECTION, fix_winding=True)
            base = op(base, rect(cx - hw, -1000, cx + hw, top + 5), pathops.PathOp.INTERSECTION)
            if not below.bounds == (0, 0, 0, 0):
                over = below.bounds[2] - (cx + hw)
                if over > 0:
                    below = transformed(below, lambda x, d=over: x - d)
                base = op(base, below, pathops.PathOp.UNION)
        dx = HALF / 2 - cx
        shift = lambda x, dx=dx: x + dx
        acc_dx = dx
        u = rev.get(name) or rev.get(name.split(".")[0])
        if top is not None and r and base_char(chr(u)) in I_DOT if u else False:
            # the flag pulls the top of i to the left: set the dot a little left of the stem
            acc_dx -= 0.3 * (hw - (r[0][1] - r[0][0]) / 2)
        if acc.bounds != (0, 0, 0, 0) and acc.bounds[2] - acc.bounds[0] > HALF - 20:
            # two dots wider than the half cell: bring them closer
            parts = list(acc.contours)
            aw = acc.bounds[2] - acc.bounds[0]
            dw = max(c.bounds[2] - c.bounds[0] for c in parts)
            kk = (HALF - 20 - dw) / max(1, aw - dw)
            ac = (acc.bounds[0] + acc.bounds[2]) / 2
            squeezed = pathops.Path()
            for c in parts:
                cc = (c.bounds[0] + c.bounds[2]) / 2
                squeezed = op(squeezed, transformed(c, lambda x, d=(ac + (cc - ac) * kk) - cc: x + d), pathops.PathOp.UNION)
            acc = squeezed
        put(f, name, op(transformed(base, shift), transformed(acc, lambda x, d=acc_dx: x + d), pathops.PathOp.UNION), HALF)
        moves[name] = shift

    # --- wide --------------------------------------------------------------
    def leg_thickness(G, top):
        import math
        y_a, y_b = top * 0.1, top * 0.3
        a, b = RD["slice_spans"](G, y_a)[-1], RD["slice_spans"](G, y_b)[-1]
        w = a[1] - a[0]
        slope = ((a[0] + a[1]) / 2 - (b[0] + b[1]) / 2) / (y_a - y_b)
        return w / math.hypot(1, slope)

    Kp, kp = glyph_path(f, "K"), glyph_path(f, "k")
    kp = op(kp, rect(-500, -500, 1500, XH), pathops.PathOp.INTERSECTION)
    t_leg = {CAP: leg_thickness(Kp, CAP), XH: leg_thickness(kp, XH)}

    def zhe(top, margin, gap):
        """Ж on the wide cell: full stem, К-weight diagonals, stepped join."""
        rect_, diag, U, I, moved = RD["rect"], RD["diag"], RD["U"], RD["I"], RD["moved"]
        mid = WIDE / 2
        ws = H_stem if top == CAP else n_stem
        tt = t_leg[top]
        st = rect_(mid - ws / 2, 0, mid + ws / 2, top)
        jy = top * 0.48
        right_out = WIDE - margin
        inner = mid + ws / 2 + ws * gap
        arm = diag(inner, right_out - tt * 0.55, jy, top + 40, tt)
        leg = diag(inner + tt * 0.35, right_out - tt * 0.6, jy + tt * 0.3, -40, tt)
        half = U(arm, leg, rect_(mid, jy - tt * 0.05, inner + tt * 0.5, jy + tt * 0.62))
        # clip from the stem's left edge, not its axis: in the thinnest masters the
        # arm's foot reaches past the axis (inside the stem) and a clip there would
        # give it a fifth point the other masters lack
        half = I(half, rect_(mid - ws / 2, 0, right_out + 50, top))
        return U(st, half, moved(half, sx=-1, cx=mid))

    for name, (top, b) in wide.items():
        p = orig[name]
        base = op(p, rect(-2000, -1000, 3000, top + 25), pathops.PathOp.INTERSECTION)
        acc = op(p, rect(-2000, top + 25, 3000, 2000), pathops.PathOp.INTERSECTION)
        bx0, _, bx1, _ = base.bounds
        c0 = (bx0 + bx1) / 2
        k = (bx1 - bx0 + WIDE_BODY) / (bx1 - bx0)
        mid = WIDE / 2

        root = b if b in ZHE else None
        if root is None and b in "ӁӂӜӝ":
            root = base_char(b)
        if root in ZHE or b in ZHE:
            top_z = ZHE.get(root or b, top)
            body = op(base, rect(-2000, 0, 3000, 2000), pathops.PathOp.INTERSECTION).bounds
            margin = (WIDE - (body[2] - body[0] + WIDE_BODY)) / 2
            new = zhe(top_z, margin, ZHE_STEP_WIDE if name.endswith(".cv02") else ZHE_STEP)
            if name.endswith(".loclBGR"):                    # Bulgarian ж: stem up to the ascender
                ws = n_stem
                new = op(new, rect(WIDE / 2 - ws / 2, 0, WIDE / 2 + ws / 2, ASC), pathops.PathOp.UNION)
            tail = op(base, rect(-2000, -1000, 3000, -1), pathops.PathOp.INTERSECTION)
            if tail.area > 0:                                # Җ җ: carry the tail over
                tb = tail.bounds
                old_r = runs(op(base, rect(-2000, 0, 3000, 2000), pathops.PathOp.INTERSECTION), 2)[-1][1]
                new_r = runs(new, 2)[-1][1]
                tail = op(tail, rect(tb[0], -1, tb[2], 4), pathops.PathOp.UNION)
                new = op(new, transformed(tail, lambda x, d=new_r - old_r: x + d), pathops.PathOp.UNION)
            shift = lambda x, d=mid - c0: x + d
            put(f, name, op(new, transformed(acc, shift), pathops.PathOp.UNION), WIDE)
            moves[name] = lambda x, c0=c0, k=k: mid + (x - c0) * k
            continue

        # stroke thickness to keep (or, for the three-stem letters, to reach)
        family = n_stem if top == XH else H_stem
        t_own = stroke_at(base, top * 0.3) or family
        if t_own > family * 1.3:                             # a junction, not a stroke
            t_own = stroke_at(base, top * 0.6) or family
        if t_own > family * 1.3:
            t_own = family
        extra = (family - t_own) if b in REWEIGHT else 0.0
        if VARIABLE:
            g, acc_g = split_tt(orig_tt[name], top + 25)
            # each stroke at its own thickness: the masters keep Paper's
            # crossing inner joins, where the statics' merged outline happened
            # to cap the thinning of W's lighter inner diagonals
            local = local_strokes(g, t_own)
        else:
            g = ttfGlyphFromSkPath(pathops.simplify(base, fix_winding=True, clockwise=True))
            # each stroke at its own thickness here too: with Ferrum's contrast
            # the diagonals are no longer the stems' weight, and one p_ref for
            # all would leave the heavy ones heavier still after the stretch.
            # The merged outline's rays can run through a join (М's diagonals
            # read 1.4x), so each reading stays within what the contrast makes
            # of a stroke: at most about 8% over the stem, 10% under
            local = {i: min(max(v, 0.90 * t_own), 1.08 * t_own) for i, v in local_strokes(g, t_own).items()}
        g.coordinates = type(g.coordinates)([(mid + (x - c0) * k, y) for x, y in g.coordinates])
        compensate(g, k, t_own, max(0.0, extra), local)
        shift = lambda x, d=mid - c0: x + d
        if VARIABLE:
            # no round trip through pathops: the master's own points, as moved
            if acc_g is not None:
                acc_g.coordinates = type(acc_g.coordinates)([(shift(x), y) for x, y in acc_g.coordinates])
            put_glyph(f, name, g, acc_g, WIDE)
        else:
            new = pathops.Path(); g.draw(new.getPen(), glyf)
            put(f, name, op(new, transformed(acc, shift), pathops.PathOp.UNION), WIDE)
        moves[name] = lambda x, c0=c0, k=k: mid + (x - c0) * k

    move_anchors(f, moves)

    # --- small caps (smcp, c2sc) ----------------------------------------------
    def vbar(name, x):
        pth = glyph_path(f, name)
        s_ = op(pth, rect(x - 0.5, -1000, x + 0.5, 2000), pathops.PathOp.INTERSECTION)
        top_c = max(s_.contours, key=lambda c: c.bounds[3]).bounds
        return top_c[3] - top_c[1]
    e_bar, z_bar = vbar("E", 400), vbar("z", 300)
    s0 = SC_H / CAP
    dy = max(0.0, z_bar - e_bar * s0)
    sc_s = (SC_H - dy) / CAP
    sc_x = min(1.0, sc_s * 1.15)                        # a little wider: they sit in a full cell
    dx = max(0.0, n_stem * 0.97 - H_stem * sc_x)
    smcp, c2sc, sc_names = {}, {}, {}
    for u, cap in sorted(cmap.items()):
        ch = chr(u)
        if not (ch.isupper() and unicodedata.category(ch) == "Lu"):
            continue
        low = ch.lower()
        if len(low) != 1 or ord(low) not in cmap:
            continue
        src_path = orig[cap] if cap in wide else glyph_path(f, cap)
        adv = HALF if cap in narrow else CELL
        if VARIABLE:
            # the master's own points: scaled and offset, no boolean / simplify
            tt = orig_tt[cap] if cap in wide else glyf[cap].getCoordinates(glyf)
            g, acc_g = split_tt(tt, CAP + 5)
            gb = [x for x, _ in g.coordinates]
            cx = (min(gb) + max(gb)) / 2
            sx = sc_x if adv == CELL else sc_s
            g.coordinates = type(g.coordinates)([(adv / 2 + (x - cx) * sx, y * sc_s) for x, y in g.coordinates])
            offset_edges(g, lambda n: dx / 2 * abs(n[0]) + dy / 2 * abs(n[1]))
            g.coordinates = type(g.coordinates)([(x, y + dy / 2) for x, y in g.coordinates])
            if acc_g is not None:
                acc_g.coordinates = type(acc_g.coordinates)(
                    [(adv / 2 + (x - cx) * sc_s, (y - CAP) * sc_s + SC_H + dy / 2) for x, y in acc_g.coordinates])
            name = cap + ".sc"
            if name not in f["glyf"]:
                f.setGlyphOrder(f.getGlyphOrder() + [name])
            put_glyph(f, name, g, acc_g, adv)
            smcp[cmap[ord(low)]] = name; c2sc[cap] = name; sc_names[name] = adv
            continue
        body = op(src_path, rect(-2000, -1000, 3000, CAP + 5), pathops.PathOp.INTERSECTION)
        acc = op(src_path, rect(-2000, CAP + 5, 3000, 2000), pathops.PathOp.INTERSECTION)
        bx0, _, bx1, _ = body.bounds
        cx = (bx0 + bx1) / 2
        sx = sc_x if adv == CELL else sc_s
        g = ttfGlyphFromSkPath(pathops.simplify(body, fix_winding=True, clockwise=True))
        g.coordinates = type(g.coordinates)([(adv / 2 + (x - cx) * sx, y * sc_s) for x, y in g.coordinates])
        offset_edges(g, lambda n: dx / 2 * abs(n[0]) + dy / 2 * abs(n[1]))   # stems to the lowercase weight
        g.coordinates = type(g.coordinates)([(x, y + dy / 2) for x, y in g.coordinates])
        pth = pathops.Path(); g.draw(pth.getPen(), glyf)
        if acc.bounds != (0, 0, 0, 0):                     # accents: scaled only, set on the small cap
            pth = op(pth, transformed_xy(acc, lambda x, y: (adv / 2 + (x - cx) * sc_s, (y - CAP) * sc_s + SC_H + dy / 2)),
                     pathops.PathOp.UNION)
        name = add_glyph(f, cap + ".sc", pth, adv)
        smcp[cmap[ord(low)]] = name; c2sc[cap] = name; sc_names[name] = adv
    # marks on small caps: centred at the small-cap height
    from fontTools.ttLib.tables import otTables as ot
    for lk in f["GPOS"].table.LookupList.Lookup:
        for st in lk.SubTable:
            if type(st).__name__ != "MarkBasePos" or "acutecomb" not in st.MarkCoverage.glyphs:
                continue
            bases = dict(zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord))
            for name, adv in sc_names.items():
                a = ot.Anchor(); a.Format = 1; a.XCoordinate = round(adv / 2); a.YCoordinate = SC_H
                r = ot.BaseRecord(); r.BaseAnchor = [a]; bases[name] = r
            names_ = sorted(bases, key=f.getGlyphID)
            st.BaseCoverage.glyphs = names_
            st.BaseArray.BaseRecord = [bases[n] for n in names_]; st.BaseArray.BaseCount = len(names_)

    # --- proportional 1 (pnum) on the half cell ---------------------------------
    # the base serif goes (trimmed it would read as l), the flag stays
    one = glyph_path(f, "one")
    st0, st1 = runs(one, CAP * 0.45)[0]
    base_top = next(y for y in range(0, 300, 4) if (lambda r: r and r[0][1] - r[0][0] < (st1 - st0) * 1.5)(runs(one, y)))
    one_n = op(op(one, rect(-1000, base_top, 2000, 2000), pathops.PathOp.INTERSECTION),
               rect(st0, 0, st1, base_top + 2), pathops.PathOp.UNION)
    one_n = op(one_n, rect(st1 - (HALF - 50), -1000, 2000, 2000), pathops.PathOp.INTERSECTION)
    ob = RD["merged"](one_n).bounds
    add_glyph(f, "one.pnum", transformed(one_n, lambda x, d=HALF / 2 - (ob[0] + ob[2]) / 2: x + d), HALF)

    # --- features: kerning on by default; mono-only sets out -----------------
    gpos = f["GPOS"].table
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == "ss20":
            fr.FeatureTag = "kern"; fr.Feature.FeatureParams = None
    drop_features(f, "GSUB", {"ss02", "ss03"})              # duospace M W, narrow space: built in now
    add_single_feature(f, "c2sc", c2sc, first=True)
    add_single_feature(f, "smcp", smcp, first=True)
    add_single_feature(f, "pnum", {"one": "one.pnum"})
    sort_features(f)

    # --- metadata ----------------------------------------------------------
    f["post"].isFixedPitch = 0
    f["OS/2"].panose.bProportion = 3
    f["OS/2"].recalcAvgCharWidth(f)
    f["head"].fontRevision = float(VERSION)
    n = f["name"]
    for r in n.names:
        s = r.toUnicode()
        if r.nameID == 5:
            s = f"Version {VERSION}; based on Ferrum Mono"
        elif r.nameID == 3:
            s = s.replace("FerrumMono", "FerrumTrio").split(";")[0] + f";{VERSION}"
        elif r.nameID == 10:
            s = ("Ferrum Trio: the letters of Ferrum Mono on three widths (half, one and a half cell). "
                 "Based on Paper Mono, with Cyrillic adapted from Geist Mono. Not affiliated with or "
                 "endorsed by Paper (Lost Coast Labs, Inc.) or Vercel.")
        else:
            s = s.replace("Ferrum Mono", "Ferrum Trio").replace("FerrumMono", "FerrumTrio")
        r.string = s
    f.save(dst)
    return len(narrow), len(wide)


os.makedirs(DST, exist_ok=True)
for p in sorted(p for p in glob.glob(os.path.join(SRC, "FerrumMono-*.ttf")) if not p.endswith("Italic.ttf")):
    out = os.path.join(DST, os.path.basename(p).replace("FerrumMono", "FerrumTrio"))
    nn, nw = build(p, out)
    print(os.path.basename(out), f"narrow {nn}, wide {nw}")
