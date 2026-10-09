"""Redraw problem Cyrillic glyphs from Paper Mono's own Latin outlines.

К к   Paper K / k (k cut at x-height)
Ж ж   centre stem + К-style diagonals, drawn with Paper's diagonal angle, lighter;
      the diagonals step away from the stem on a short shelf. cv02: the step
      spread wider (Ж ж Җ җ)
И и   full-weight stems, lighter diagonal (upstroke), not a mirrored N
Ч ч   Paper U / u bowl raised, cut at the right stem, straight right stem
Ф ф   Paper o split at the centre and widened, lighter stem through it
Й й Ѝ ѝ Ӣ ӣ Ў ў   accents taken from Paper (Ă ă, È è, Ā ā, Ŭ ŭ)
Қ қ Җ җ Ҷ ҷ   tails carried over from the existing glyphs

With --variable (masters of the variable font) the letters are kept as
overlapping parts -- stems, diagonals, shelves, bowl halves -- each clipped on
its own, instead of being merged into one outline: merging gives every weight
a different point structure, and a variable font needs them identical.
"""
import sys, glob, math, io
import pathops
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib.removeOverlaps import skPathFromGlyph, ttfGlyphFromSkPath

CAP, XH = 710, 509


VARIABLE = "--variable" in sys.argv[2:]


def _parts(p):
    return p if isinstance(p, list) else [p]


def _empty(p):
    return p.bounds == (0, 0, 0, 0)


def P(font, ch_or_name):
    name = ch_or_name if len(ch_or_name) > 1 else font.getBestCmap()[ord(ch_or_name)]
    return skPathFromGlyph(name, font.getGlyphSet())


def rect(x0, y0, x1, y1):
    p = pathops.Path()
    p.moveTo(x0, y0); p.lineTo(x0, y1); p.lineTo(x1, y1); p.lineTo(x1, y0); p.close()
    return p


def poly(pts):
    p = pathops.Path()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    return p


def U(*ps):
    if VARIABLE:                                   # overlapping parts, not merged
        return [q for p in ps for q in _parts(p) if not _empty(q)]
    out = pathops.Path()
    for p in ps:
        out = pathops.op(out, p, pathops.PathOp.UNION, fix_winding=True)
    return out


def I(a, b):
    if isinstance(a, list):                        # clip every part on its own
        return [q for q in (I(x, b) for x in a) if not _empty(q)]
    if VARIABLE:
        # contours the clip does not cross pass through untouched; only the
        # crossed ones go through the boolean op
        bx0, by0, bx1, by1 = b.bounds
        keep, cut = pathops.Path(), pathops.Path()
        for c in a.contours:
            x0, y0, x1, y1 = c.bounds
            if x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1:
                c.draw(keep.getPen())
            elif not (x1 <= bx0 or x0 >= bx1 or y1 <= by0 or y0 >= by1):
                c.draw(cut.getPen())
        if not _empty(cut):
            # the op's own output runs counter-clockwise; turn it like the rest
            pathops.simplify(pathops.op(cut, b, pathops.PathOp.INTERSECTION, fix_winding=True),
                             fix_winding=True, clockwise=True).draw(keep.getPen())
        return keep
    return pathops.op(a, b, pathops.PathOp.INTERSECTION, fix_winding=True)


def D(a, b):
    if isinstance(a, list):
        return [q for q in (D(x, b) for x in a) if not _empty(q)]
    return pathops.op(a, b, pathops.PathOp.DIFFERENCE, fix_winding=True)


def merged(p):
    """One outline from overlapping parts (for measuring only)."""
    if not isinstance(p, list):
        return p
    out = pathops.Path()
    for q in p:
        out = pathops.op(out, q, pathops.PathOp.UNION, fix_winding=True)
    return out


def moved(p, dx=0, dy=0, sx=1, cx=0):
    if isinstance(p, list):
        return [moved(x, dx, dy, sx, cx) for x in p]
    q = pathops.Path()
    pen = q.getPen()

    class T:
        def _f(self, pts):
            return [((x - cx) * sx + cx + dx, y + dy) for x, y in pts]
        def moveTo(self, pt): pen.moveTo(*self._f([pt]))
        def lineTo(self, pt): pen.lineTo(*self._f([pt]))
        def qCurveTo(self, *pts): pen.qCurveTo(*self._f(pts))
        def curveTo(self, *pts): pen.curveTo(*self._f(pts))
        def closePath(self): pen.closePath()
        def endPath(self): pen.endPath()
    p.draw(T())
    return q


def bounds(p):
    return merged(p).bounds  # (xMin, yMin, xMax, yMax)


def slice_spans(p, y, h=4):
    """x-spans where the outline is filled at height y."""
    s = I(merged(p), rect(-500, y - h / 2, 1500, y + h / 2))
    return sorted((c.bounds[0], c.bounds[2]) for c in s.contours)


def diag(x_bot, x_top, y0, y1, t):
    """Parallelogram stroke with perpendicular thickness t; centreline from
    (x_bot, y0) to (x_top, y1); ends cut horizontally."""
    dx, dy = x_top - x_bot, y1 - y0
    L = math.hypot(dx, dy)
    hw = t * L / abs(dy) / 2  # half horizontal width
    return poly([(x_bot - hw, y0), (x_top - hw, y1), (x_top + hw, y1), (x_bot + hw, y0)])


def outline(path):
    """TrueType direction: outer contours clockwise. Variable masters: overlaps
    kept; each part is turned as a whole so that its largest (outer) contour
    runs clockwise -- counters inside a part keep running the other way."""
    if not VARIABLE:
        return pathops.simplify(merged(path), fix_winding=True, clockwise=True)
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.reverseContourPen import ReverseContourPen
    from fontTools.pens.areaPen import AreaPen
    out = pathops.Path()
    for part in _parts(path):
        recs = []
        for c in part.contours:
            rec = RecordingPen(); c.draw(rec)
            ap = AreaPen(); rec.replay(ap)               # > 0: counter-clockwise
            recs.append((rec, ap.value))
        if not recs:
            continue
        flip = max(recs, key=lambda r: abs(r[1]))[1] > 0
        for rec, _ in recs:
            rec.replay(ReverseContourPen(out.getPen()) if flip else out.getPen())
    return out


def ttglyph(path):
    """Glyph from a path. Variable masters: every on-curve point implied
    between two off-curves is written out, so the point structure does not
    depend on how the coordinates happened to round in each weight."""
    if not VARIABLE:
        return ttfGlyphFromSkPath(outline(path))
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    pen = TTGlyphPen(None); outline(path).draw(pen)
    g = pen.glyph(dropImpliedOnCurves=False)       # keep start points where they are
    if g.numberOfContours <= 0:
        return g
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
    pts, flags, ends, start = [], [], [], 0
    for end in g.endPtsOfContours:
        c = [(tuple(g.coordinates[i]), g.flags[i] & 1) for i in range(start, end + 1)]
        cc = []
        for i, (pt, on) in enumerate(c):
            cc.append((pt, on))
            nxt, non = c[(i + 1) % len(c)]
            if not on and not non:
                cc.append((((pt[0] + nxt[0]) / 2, (pt[1] + nxt[1]) / 2), 1))
        # the same start in every weight: the leftmost of the lowest on-curve
        # points (within 8 units of the lowest, so near-ties do not flip)
        ons = [i for i, (pt, on) in enumerate(cc) if on]
        low = min(cc[i][0][1] for i in ons)
        k = min((i for i in ons if cc[i][0][1] <= low + 8), key=lambda i: (cc[i][0][0], cc[i][0][1]))
        cc = cc[k:] + cc[:k]
        pts += [pt for pt, on in cc]; flags += [on for pt, on in cc]
        ends.append(len(pts) - 1)
        start = end + 1
    out = Glyph(); out.numberOfContours = len(ends); out.endPtsOfContours = ends
    out.coordinates = GlyphCoordinates([(round(x), round(y)) for x, y in pts])
    out.flags = bytearray(flags); out.program = g.program
    return out


def put(font, u, path, adv):
    cmap = font.getBestCmap()
    if u not in cmap:
        return
    name = cmap[u]
    g = ttglyph(path)
    font["glyf"][name] = g
    g.recalcBounds(font["glyf"])
    font["hmtx"][name] = (adv, getattr(g, "xMin", 0))


def add_glyph(font, name, path, adv):
    """A new unencoded glyph (alternate)."""
    if name not in font["glyf"]:
        font.setGlyphOrder(font.getGlyphOrder() + [name])
    g = ttglyph(path)
    font["glyf"][name] = g
    g.recalcBounds(font["glyf"])
    font["hmtx"][name] = (adv, getattr(g, "xMin", 0))
    return name


def add_cv(font, tag, label, mapping):
    """Graft a character-variant feature (single substitutions) into GSUB."""
    subs = "\n".join(f"    sub {a} by {b};" for a, b in sorted(mapping.items()))
    fea = (f"feature {tag} {{\n    cvParameters {{ FeatUILabelNameID {{ name \"{label}\"; }}; }};\n"
           f"{subs}\n}} {tag};\n")
    buf = io.BytesIO(); font.save(buf); buf.seek(0); tmp = TTFont(buf)
    del tmp["GSUB"]
    addOpenTypeFeaturesFromString(tmp, fea, tables=["GSUB"])
    orig, new = font["GSUB"].table, tmp["GSUB"].table
    off = len(orig.LookupList.Lookup)
    orig.LookupList.Lookup.extend(new.LookupList.Lookup)
    orig.LookupList.LookupCount = len(orig.LookupList.Lookup)
    for fr in new.FeatureList.FeatureRecord:
        fr.Feature.LookupListIndex = [i + off for i in fr.Feature.LookupListIndex]
        orig.FeatureList.FeatureRecord.append(fr)
    orig.FeatureList.FeatureCount = len(orig.FeatureList.FeatureRecord)
    fi = orig.FeatureList.FeatureCount - 1
    for sr in orig.ScriptList.ScriptRecord:
        for ls in [sr.Script.DefaultLangSys] + [r.LangSys for r in sr.Script.LangSysRecord]:
            if ls is not None:
                ls.FeatureIndex.append(fi); ls.FeatureCount = len(ls.FeatureIndex)
    font["name"] = tmp["name"]


def accent(font, base_latin, letter_latin, above):
    """The accent part of a Paper accented glyph (everything above `above`)."""
    return I(P(font, base_latin), rect(-500, above, 1500, 2000))


def tail(font, u, base_new):
    """Carry over the descender tail of an existing glyph, aligned to the new base."""
    cmap = font.getBestCmap()
    old = skPathFromGlyph(cmap[u], font.getGlyphSet())
    t = I(old, rect(-500, -1000, 1500, -1))
    if t.area == 0:
        return base_new
    tb = bounds(t)
    # right edge of new base at baseline
    nb = slice_spans(base_new, 2)
    ob = slice_spans(I(old, rect(-500, 0, 1500, 2000)), 2)
    shift = nb[-1][1] - ob[-1][1]
    # tail extends up to the baseline so it fuses with the base
    t = U(t, rect(tb[0], -1, tb[2], 4))
    return U(base_new, moved(t, dx=shift))


def build(path):
    f = TTFont(path)
    adv = f["hmtx"]["uni0410"][0]
    mid = adv / 2

    H = P(f, "H"); n = P(f, "n"); K = P(f, "K"); k = P(f, "k")
    Uc = P(f, "U"); uc = P(f, "u"); o = P(f, "o")

    hl, hr = slice_spans(H, 600)[0], slice_spans(H, 600)[-1]   # H stems
    nl, nr = slice_spans(n, 200)[0], slice_spans(n, 200)[-1]   # n stems
    S = hl[1] - hl[0]            # cap stem
    s = nl[1] - nl[0]            # lowercase stem
    kb = bounds(K); lkb = bounds(k)

    # --- К к -------------------------------------------------------------
    put(f, 0x041A, K, adv)
    kk = I(k, rect(-500, -500, 1500, XH))
    put(f, 0x043A, kk, adv)

    # diagonal thickness of Paper K's lower leg, measured perpendicular
    def leg_thickness(G, top):
        y_a, y_b = top * 0.1, top * 0.3
        a, b = slice_spans(G, y_a)[-1], slice_spans(G, y_b)[-1]
        w = a[1] - a[0]
        slope = ((a[0] + a[1]) / 2 - (b[0] + b[1]) / 2) / (y_a - y_b)
        return w / math.hypot(1, slope)

    tK, tk = leg_thickness(K, CAP), leg_thickness(kk, XH)

    # --- Ж ж -------------------------------------------------------------
    # (stem factor, diagonal factor, step gap x stem)
    ZHE_STEP, ZHE_STEP_WIDE = (0.80, 0.84, 0.30), (0.72, 0.80, 0.55)

    def zhe(top, stem, t, margin, shape):
        kws, ktt, kgap = shape
        ws = stem * kws
        st = rect(mid - ws / 2, 0, mid + ws / 2, top)
        jy = top * 0.48
        tt = t * ktt
        right_out = adv - margin
        inner = mid + ws / 2 + stem * kgap
        arm = diag(inner, right_out - tt * 0.55, jy, top + 40, tt)
        leg = diag(inner + tt * 0.35, right_out - tt * 0.6, jy + tt * 0.3, -40, tt)
        # the shelf: the step that joins the diagonals to the stem
        half = U(arm, leg, rect(mid, jy - tt * 0.05, inner + tt * 0.5, jy + tt * 0.62))
        half = I(half, rect(mid, 0, right_out + 50, top))
        other = moved(half, sx=-1, cx=mid)
        return U(st, half, other)

    put(f, 0x0416, zhe(CAP, S, tK, 20, ZHE_STEP), adv)
    put(f, 0x0436, zhe(XH, s, tk, 28, ZHE_STEP), adv)
    Жw, жw = zhe(CAP, S, tK, 20, ZHE_STEP_WIDE), zhe(XH, s, tk, 28, ZHE_STEP_WIDE)

    # --- И и -------------------------------------------------------------
    def i_letter(top, l, r, stem):
        ls = rect(l[0], 0, l[1], top)
        rs = rect(r[0], 0, r[1], top)
        t = stem * 0.78
        # centreline: inside the left stem at the foot, inside the right stem at the top
        hw_guess = t * 1.25
        d = diag(l[1] - hw_guess * 0.35, r[0] + hw_guess * 0.35, 0, top, t)
        d = I(d, rect(l[0], 0, r[1], top))
        return U(ls, rs, d)

    И = i_letter(CAP, hl, hr, S)
    и = i_letter(XH, nl, nr, s)
    put(f, 0x0418, И, adv)
    put(f, 0x0438, и, adv)

    # --- Ч ч -------------------------------------------------------------
    def che(Ushape, top, raise_by, stem_slice_y):
        r = slice_spans(Ushape, stem_slice_y)[-1]
        # variable masters: the right stem covers the bowl's right edge anyway,
        # and a vertical cut through the curve changes topology from weight to weight
        bowl = I(moved(Ushape, dy=raise_by), rect(-500, 0, 1500 if VARIABLE else r[0] + 1, top))
        return U(bowl, rect(r[0], 0, r[1], top))

    Ч = che(Uc, CAP, CAP * 0.36, 600)
    ч = che(uc, XH, XH * 0.36, 400)
    put(f, 0x0427, Ч, adv)
    put(f, 0x0447, ч, adv)

    # --- Ф ф -------------------------------------------------------------
    # Ф ф may not reach closer to the cell edge than Paper's own x / X do
    sb_min = min(bounds(P(f, "x"))[0], bounds(P(f, "X"))[0])

    def ef(stem, y0, y1, dy):
        ob = bounds(o)
        delta = min(stem * 0.75, adv - 2 * sb_min - (ob[2] - ob[0]))
        left = moved(I(o, rect(-500, -500, mid, 2000)), dx=-delta / 2, dy=dy)
        right = moved(I(o, rect(mid, -500, 1500, 2000)), dx=delta / 2, dy=dy)
        oy0, oy1 = ob[1] + dy, ob[3] + dy
        # bridge the split at top and bottom (hidden under the stem anyway)
        ws = stem * 0.86
        st = rect(mid - ws / 2, y0, mid + ws / 2, y1)
        return U(left, right, st)

    o_h = bounds(o)[3] - bounds(o)[1]
    Ф = ef(S, 0, CAP, (CAP - o_h) / 2 - bounds(o)[1])
    ф = ef(s, -182, 747, 0)
    put(f, 0x0424, Ф, adv)
    put(f, 0x0444, ф, adv)

    # --- accented ---------------------------------------------------------
    put(f, 0x0419, U(И, accent(f, "Abreve", "A", CAP + 20)), adv)
    put(f, 0x0439, U(и, accent(f, "abreve", "a", XH + 40)), adv)
    put(f, 0x040D, U(И, accent(f, "Egrave", "E", CAP + 20)), adv)
    put(f, 0x045D, U(и, accent(f, "egrave", "e", XH + 40)), adv)
    cm = f.getBestCmap()
    # Ў ў: Geist's У у with Paper's breve, placed as on Ŭ ŭ
    for u, ch, latin, base_latin, top in ((0x040E, "У", "Ubreve", "U", CAP), (0x045E, "у", "ubreve", "u", XH)):
        body = I(P(f, ch), rect(-500, -1000, 1500, top + 20))
        acc = accent(f, latin, base_latin, top + (20 if top == CAP else 40))
        dx = mid - (bounds(acc)[0] + bounds(acc)[2]) / 2
        put(f, u, U(body, moved(acc, dx=dx)), adv)
    if 0x100 in cm:
        put(f, 0x04E2, U(И, accent(f, "Amacron", "A", CAP + 20)), adv)
        put(f, 0x04E3, U(и, accent(f, "amacron", "a", XH + 40)), adv)

    # --- tails ------------------------------------------------------------
    Ж = skPathFromGlyph(cm[0x0416], f.getGlyphSet())
    ж = skPathFromGlyph(cm[0x0436], f.getGlyphSet())
    for u, base in ((0x049A, K), (0x049B, kk), (0x0496, Ж), (0x0497, ж)):
        put(f, u, tail(f, u, base), adv)

    # cv02 alternates
    alts = {}
    for u, path_ in ((0x0416, Жw), (0x0436, жw), (0x0496, tail(f, 0x0496, Жw)), (0x0497, tail(f, 0x0497, жw))):
        alts[cm[u]] = add_glyph(f, cm[u] + ".cv02", path_, adv)
    add_cv(f, "cv02", "Ж with a wide step", alts)

    # Ҷ ҷ: same tail as Ц ц, placed against Ч's right stem
    for u, base, tse, slice_y in ((0x04B6, Ч, 0x0426, 400), (0x04B7, ч, 0x0446, 300)):
        ts = skPathFromGlyph(cm[tse], f.getGlyphSet())
        tl = I(ts, rect(-500, -1000, 1500, -1))
        tb = bounds(tl)
        tl = U(tl, rect(tb[0], -1, tb[2], 4))
        dx = slice_spans(base, 100)[-1][1] - slice_spans(ts, slice_y)[-1][1]
        # bottom bar thickness of Ц: vertical slice through the middle
        bh = I(ts, rect(mid - 2, -500, mid + 2, 2000)).bounds[3]
        stem_r = slice_spans(base, 100)[-1][1]
        tr = bounds(moved(tl, dx=dx))[2]
        shelf = rect(stem_r - 2, 0, tr, bh)
        put(f, u, U(base, moved(tl, dx=dx), shelf), adv)

    f.save(path)


for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    build(p)
    print("redrawn", p)
