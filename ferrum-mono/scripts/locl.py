"""Localized Cyrillic forms (GSUB locl under the 'cyrl' script).

Bulgarian (BGR), the modern Bulgarian lowercase as in Geologica, Montserrat,
Commissioner (Google Fonts):
    и й ѝ п т к д   -> Paper's own u ŭ ù n m k g
    л  ʌ (v turned)           ш  ɯ (m turned)       щ  ɯ with the ц tail
    ц  u with the ц tail      ж  stem up to the ascender
    ю  stem up to the ascender                      з  ʒ (З set on the descender)
    в  B-form with ascender   г  ƨ (s mirrored)
    Д  Δ on Д's feet          Л  Λ (V turned)
Serbian (SRB): б  δ (ð mirrored, without its bar).
Macedonian (MKD): ѓ with a steeper acute.
Italic-only Serbian / Macedonian forms (г д п т) are out of scope: no italic.

With --variable (masters of the variable font) nothing is merged or cleaned:
the forms are kept as overlapping parts with the same point structure in every
weight (redraw.py's variable mode), and ð's bar -- an overlapping contour of
its own in Paper's variable font -- is simply left out.
"""
import sys, glob, os, math
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.removeOverlaps import ttfGlyphFromSkPath

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_rd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "redraw.py")
_src = open(_rd, encoding="utf-8").read()
RD = {}
exec(compile(_src[:_src.index("\nfor p in sorted(glob.glob")], _rd, "exec"), RD)
P, rect, U, I, D, moved, spans, add_glyph = (RD[k] for k in ("P", "rect", "U", "I", "D", "moved", "slice_spans", "add_glyph"))
VARIABLE = RD["VARIABLE"]
to_tt = RD["ttglyph"] if VARIABLE else ttfGlyphFromSkPath

CAP, XH, ASC = 710, 509, 747


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


def tf(path, fx=lambda x, y: x, fy=lambda x, y: y):
    """Path with every point mapped (contour direction fixed afterwards by add_glyph)."""
    out = pathops.Path(); pen = out.getPen()
    m = lambda p: (fx(*p), fy(*p))

    class T:
        def moveTo(self, p): pen.moveTo(m(p))
        def lineTo(self, p): pen.lineTo(m(p))
        def qCurveTo(self, *ps): pen.qCurveTo(*[None if p is None else m(p) for p in ps])
        def curveTo(self, *ps): pen.curveTo(*[m(p) for p in ps])
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    path.draw(T())
    if VARIABLE:
        return out                       # direction is set per contour when the glyph is written
    return pathops.simplify(out, fix_winding=True, clockwise=True)


def bounds(p):
    return p.bounds


def narrow_to(path, x0, x1, stroke):
    """Horizontal squeeze into [x0, x1], vertical edges pulled back out so the
    strokes keep about their weight (edge offset along the normal)."""
    b = path.bounds
    k = (x1 - x0) / (b[2] - b[0])
    sq = tf(path, fx=lambda x, y: x0 + (x - b[0]) * k)
    if abs(k - 1) < 0.02 and not VARIABLE:
        return sq
    g = to_tt(sq)
    pts = [tuple(map(float, q)) for q in g.coordinates]
    out = list(pts); start = 0
    for end in g.endPtsOfContours:
        n = end - start + 1
        for i in range(n):
            a, bb, c = pts[start + (i - 1) % n], pts[start + i], pts[start + (i + 1) % n]
            def nrm(p, q):
                tx, ty = q[0] - p[0], q[1] - p[1]; L = math.hypot(tx, ty) or 1
                return -ty / L, tx / L
            n1, n2 = nrm(a, bb), nrm(bb, c)
            d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
            if d > 0.2:
                out[start + i] = (bb[0] + (n1[0] + n2[0]) / d * stroke * (1 - k) / 2, bb[1])
        start = end + 1
    g.coordinates = type(g.coordinates)([(round(x), round(y)) for x, y in out])
    res = pathops.Path(); g.draw(res.getPen(), None)
    return res


def stretch_up(path, y_split, y_old, y_new, p_ref):
    """Stretch everything above y_split so y_old lands on y_new, then move the
    edges up there along their normals so horizontal strokes keep p_ref."""
    k = (y_new - y_split) / (y_old - y_split)
    up = tf(path, fy=lambda x, y: y if y <= y_split else y_split + (y - y_split) * k)
    g = to_tt(up)
    pts = [tuple(map(float, q)) for q in g.coordinates]
    out = list(pts); start = 0

    def edge(a, b):
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        if L < 1e-6 or min(a[1], b[1]) < y_split + 2:
            return None if L < 1e-6 else ((-ty / L, tx / L), 0.0)
        n = (-ty / L, tx / L); sp = abs(n[1])
        if sp < 1e-3:
            return n, 0.0
        if sp > 0.9999:
            return n, p_ref / 2 * (1 - k)
        tp = sp / math.sqrt(1 - sp * sp)
        sth = k * tp / math.hypot(1, k * tp)
        return n, p_ref / 2 * (1 - k * sp / sth)

    for end in g.endPtsOfContours:
        n_pts = end - start + 1
        for i in range(n_pts):
            a, b, c = pts[start + (i - 1) % n_pts], pts[start + i], pts[start + (i + 1) % n_pts]
            e1, e2 = edge(a, b), edge(b, c)
            if e1 is None or e2 is None:
                continue
            (n1, q1), (n2, q2) = e1, e2
            det = n1[0] * n2[1] - n1[1] * n2[0]
            if abs(det) < 0.05:
                n = ((n1[0] + n2[0]) / 2, (n1[1] + n2[1]) / 2); q = (q1 + q2) / 2
                out[start + i] = (b[0] + n[0] * q, b[1] + n[1] * q)
            else:
                dx = (q1 * n2[1] - q2 * n1[1]) / det; dy = (n1[0] * q2 - n2[0] * q1) / det
                if VARIABLE:
                    # spike guard: the variable masters are not simplified afterwards
                    lim = 3 * max(abs(q1), abs(q2), 1)
                    if math.hypot(dx, dy) > lim:
                        kk = lim / math.hypot(dx, dy); dx, dy = dx * kk, dy * kk
                out[start + i] = (b[0] + dx, b[1] + dy)
        start = end + 1
    g.coordinates = type(g.coordinates)([(round(x), round(y)) for x, y in out])
    res = pathops.Path(); g.draw(res.getPen(), None)
    return res


def stretch_up_var(path, y_split, y_old, y_new, y_bar):
    """Variable masters: the same raise as stretch_up, point by point -- below
    y_split nothing moves, the top bar (above y_bar, its underside) moves up
    whole, the sides in between stretch. Stroke thicknesses stay exact and the
    point structure is untouched."""
    d = y_new - y_old
    k = (y_bar + d - y_split) / (y_bar - y_split)
    def fy(x, y):
        if y <= y_split:
            return y
        if y >= y_bar:
            return y + d
        return y_split + (y - y_split) * k
    return tf(path, fy=fy)


def tail_of(f, u):
    """The descender tail of ц / щ / Д (+ a sliver to fuse with the baseline)."""
    t = I(P(f, f.getBestCmap()[u]), rect(-500, -1000, 1500, -1))
    tb = t.bounds
    return U(t, rect(tb[0], -1, tb[2], 6)), tb


def remove_bar(path, y_from, y_to):
    """Drop the slanted crossbar of ð. Scanning the ascender between y_from and
    y_to, the bar shows up as a second run or a jump in width; inside that band
    the ascender is redrawn as a straight stroke between the clean rows just
    below and above the bar (clipping the curved original to that stroke left
    a notch where the curve bulged out)."""
    if VARIABLE:
        # Paper's variable font draws the bar as a contour of its own
        out = pathops.Path()
        for c in path.contours:
            if c.bounds[1] < y_from - 20:
                c.draw(out.getPen())
        return out
    rows = [(y, spans(path, y, 2)) for y in range(y_from, y_to, 4)]
    clean = lambda r, ref: len(r) == 1 and (ref is None or r[0][1] - r[0][0] < 1.25 * ref)
    ref = rows[0][1][0][1] - rows[0][1][0][0]
    lo = next(y for (y, r), (_, r2) in zip(rows, rows[1:]) if not clean(r2, ref))
    top_ref = rows[-1][1][0][1] - rows[-1][1][0][0]
    hi = next(y for (y, r), (_, r2) in zip(rows[::-1], rows[::-1][1:]) if not clean(r2, top_ref))
    (b0, b1), (a0, a1) = spans(path, lo, 2)[0], spans(path, hi, 2)[0]
    stroke = pathops.Path()
    stroke.moveTo(b0 - 1, lo - 2); stroke.lineTo(a0 - 1, hi + 2); stroke.lineTo(a1 + 1, hi + 2); stroke.lineTo(b1 + 1, lo - 2); stroke.close()
    band = rect(-500, lo, 1500, hi)
    return U(D(path, band), I(stroke, band))


def add_locl(f, lang_maps):
    """One SingleSubst lookup + one 'locl' feature per language, hooked into a
    new LangSys under 'cyrl' that otherwise copies the default Cyrillic one."""
    gsub = f["GSUB"].table
    cyrl = next(r for r in gsub.ScriptList.ScriptRecord if r.ScriptTag == "cyrl").Script
    for tag, mapping in lang_maps.items():
        lk = ot.Lookup(); lk.LookupType = 1; lk.LookupFlag = 0
        st = ot.SingleSubst(); st.mapping = dict(mapping); lk.SubTable = [st]; lk.SubTableCount = 1
        gsub.LookupList.Lookup.append(lk); gsub.LookupList.LookupCount = len(gsub.LookupList.Lookup)
        fr = ot.FeatureRecord(); fr.FeatureTag = "locl"
        fr.Feature = ot.Feature(); fr.Feature.FeatureParams = None
        fr.Feature.LookupListIndex = [len(gsub.LookupList.Lookup) - 1]; fr.Feature.LookupCount = 1
        gsub.FeatureList.FeatureRecord.append(fr); gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
        ls = ot.LangSys(); ls.LookupOrder = None; ls.ReqFeatureIndex = 0xFFFF
        ls.FeatureIndex = list(cyrl.DefaultLangSys.FeatureIndex) + [gsub.FeatureList.FeatureCount - 1]
        ls.FeatureCount = len(ls.FeatureIndex)
        rec = ot.LangSysRecord(); rec.LangSysTag = tag; rec.LangSys = ls
        cyrl.LangSysRecord = [r for r in cyrl.LangSysRecord if r.LangSysTag != tag] + [rec]
        cyrl.LangSysRecord.sort(key=lambda r: r.LangSysTag); cyrl.LangSysCount = len(cyrl.LangSysRecord)
    # GPOS: the same language systems, default features (kerning, marks)
    gpos = f["GPOS"].table
    for sr in gpos.ScriptList.ScriptRecord:
        if sr.ScriptTag != "cyrl":
            continue
        for tag in lang_maps:
            ls = ot.LangSys(); ls.LookupOrder = None; ls.ReqFeatureIndex = 0xFFFF
            ls.FeatureIndex = list(sr.Script.DefaultLangSys.FeatureIndex); ls.FeatureCount = len(ls.FeatureIndex)
            rec = ot.LangSysRecord(); rec.LangSysTag = tag; rec.LangSys = ls
            sr.Script.LangSysRecord = [r for r in sr.Script.LangSysRecord if r.LangSysTag != tag] + [rec]
        sr.Script.LangSysRecord.sort(key=lambda r: r.LangSysTag); sr.Script.LangSysCount = len(sr.Script.LangSysRecord)


def anchor_new(f, names_from):
    """Top-mark anchors for the new glyphs: copied from a twin, or centred."""
    gpos = f["GPOS"].table
    for lk in gpos.LookupList.Lookup:
        for st in lk.SubTable:
            if type(st).__name__ != "MarkBasePos" or "acutecomb" not in st.MarkCoverage.glyphs:
                continue
            bases = dict(zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord))
            for new, (twin, y) in names_from.items():
                g = f["glyf"][new]; g.recalcBounds(f["glyf"])
                rec = ot.BaseRecord(); a = ot.Anchor(); a.Format = 1
                if twin in bases:
                    a.XCoordinate = bases[twin].BaseAnchor[0].XCoordinate
                else:
                    a.XCoordinate = round((g.xMin + g.xMax) / 2)
                a.YCoordinate = y
                rec.BaseAnchor = [a]; bases[new] = rec
            order = sorted(bases, key=f.getGlyphID)
            st.BaseCoverage.glyphs = order
            st.BaseArray.BaseRecord = [bases[n] for n in order]; st.BaseArray.BaseCount = len(order)


def build(path):
    f = TTFont(path)
    cm = f.getBestCmap()
    adv = f["hmtx"]["uni0410"][0]
    mid = adv / 2
    c = lambda ch: cm[ord(ch)]
    n_stem = spans(P(f, "n"), 200)[0]; n_stem = n_stem[1] - n_stem[0]
    H_stem = spans(P(f, "H"), 200)[0]; H_stem = H_stem[1] - H_stem[0]
    new = {}                         # glyph name -> (anchor twin, anchor y)
    bgr, srb, mkd = {}, {}, {}

    def make(base_ch, suffix, path_, twin=None, y=XH):
        if VARIABLE:
            name = add_glyph(f, c(base_ch) + suffix, path_, adv)
            new[name] = (twin or c(base_ch), y)
            return name
        # round to the unit grid first, then let add_glyph simplify the result
        g0 = drop_tiny(ttfGlyphFromSkPath(pathops.simplify(path_, fix_winding=True, clockwise=True)))
        path_ = pathops.Path(); g0.draw(path_.getPen(), None)
        name = add_glyph(f, c(base_ch) + suffix, path_, adv)
        new[name] = (twin or c(base_ch), y)
        return name

    # --- Bulgarian: straight to Paper's Latin --------------------------------
    for cyr, lat in (("и", "u"), ("й", "ubreve"), ("ѝ", "ugrave"), ("п", "n"), ("т", "m"), ("к", "k"), ("д", "g")):
        bgr[c(cyr)] = lat

    # л: v turned; ш: m turned (ɯ)
    lam = tf(P(f, "v"), fy=lambda x, y: XH - y)
    bgr[c("л")] = make("л", ".loclBGR", lam, "v")
    sha = tf(P(f, "m"), fy=lambda x, y: XH - y)
    bgr[c("ш")] = make("ш", ".loclBGR", sha, "m")

    # ц, щ: u / ɯ with the tail of ц, under the right stem
    tail, tb = tail_of(f, ord("ц"))
    u_path = P(f, "u")
    ur = spans(u_path, 250)[-1]
    tse = U(u_path, moved(tail, dx=ur[1] - tb[2]))
    bgr[c("ц")] = make("ц", ".loclBGR", tse, "u")
    sr_ = spans(sha, 300)[-1]
    shcha = U(sha, moved(tail, dx=sr_[1] - tb[2]))
    bgr[c("щ")] = make("щ", ".loclBGR", shcha, "m")

    # ж, ю: stem up to the ascender
    zh = P(f, c("ж")); st = spans(zh, 40); s0 = st[len(st) // 2]
    bgr[c("ж")] = make("ж", ".loclBGR", U(zh, rect(s0[0], 0, s0[1], ASC)), y=ASC)
    yu = P(f, c("ю")); s0 = spans(yu, 40)[0]
    bgr[c("ю")] = make("ю", ".loclBGR", U(yu, rect(s0[0], 0, s0[1], ASC)), y=ASC)

    # з: ʒ — the capital З set from the x-height overshoot down to g's descender
    Z = P(f, c("З")); zb = Z.bounds
    gb = P(f, "g").bounds
    ky = (521 - gb[1]) / (zb[3] - zb[1])
    ezh = tf(Z, fy=lambda x, y: gb[1] + (y - zb[1]) * ky)
    lb = P(f, c("з")).bounds
    ezh = narrow_to(ezh, lb[0], lb[2], H_stem * 0.9)
    bgr[c("з")] = make("з", ".loclBGR", ezh)

    # в: the lowercase в with its upper bowl raised to the ascender
    ve = P(f, c("в")); vb = ve.bounds
    hs = sorted(cc.bounds for cc in I(ve, rect(mid - 2, -500, mid + 2, 2000)).contours)   # bottom, middle, top bars
    mid_bar, top_bar = hs[len(hs) // 2], hs[-1]
    if VARIABLE:
        vbg = stretch_up_var(ve, mid_bar[3], vb[3], ASC, top_bar[1])
    else:
        vbg = stretch_up(ve, mid_bar[3], vb[3], ASC, top_bar[3] - top_bar[1])
    bgr[c("в")] = make("в", ".loclBGR", vbg, y=ASC)

    # г: ƨ — s mirrored
    bgr[c("г")] = make("г", ".loclBGR", tf(P(f, "s"), fx=lambda x, y: adv - x), "s")

    # Л: Λ (V turned), Л's width;  Д: Λ on Д's feet
    V = tf(P(f, "V"), fy=lambda x, y: CAP - y)
    Lb = P(f, c("Л")).bounds
    Lam = narrow_to(V, Lb[0], Lb[2], H_stem * 0.9)
    bgr[c("Л")] = make("Л", ".loclBGR", Lam, y=CAP)
    De = P(f, c("Д"))
    bar_top = [r for r in RD["I"](De, rect(mid - 2, -500, mid + 2, 300)).contours]
    bar_top = max(cc.bounds[3] for cc in bar_top) if bar_top else 90
    feet = I(De, rect(-500, -1000, 1500, bar_top))
    fb = spans(feet, bar_top / 2)
    inner = narrow_to(V, fb[0][0] + 30, fb[-1][1] - 30, H_stem * 0.9)
    bgr[c("Д")] = make("Д", ".loclBGR", U(feet, inner), y=CAP)

    # --- Serbian: б as δ (ð mirrored, its bar removed) ---------------------
    eth = remove_bar(P(f, "eth"), XH - 9, ASC - 3)
    eth = tf(eth, fx=lambda x, y: adv - x)
    srb[c("б")] = make("б", ".loclSRB", eth, y=ASC)

    # --- Macedonian: ѓ with a steeper acute ---------------------------------
    gje = P(f, c("ѓ"))
    body = I(gje, rect(-500, -1000, 1500, XH + 30))
    acc = I(gje, rect(-500, XH + 30, 1500, 2000))
    ab = acc.bounds; ac = (ab[0] + ab[2]) / 2
    steep = tf(acc, fx=lambda x, y: ac + (x - ac) * 0.55)
    mkd[c("ѓ")] = make("ѓ", ".loclMKD", U(body, steep))

    anchor_new(f, new)
    add_locl(f, {"BGR ": bgr, "SRB ": srb, "MKD ": mkd})
    f.save(path)
    return len(bgr), len(srb), len(mkd), len(new)


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    print(os.path.basename(p), "locl BGR %d, SRB %d, MKD %d; new glyphs %d" % build(p))
