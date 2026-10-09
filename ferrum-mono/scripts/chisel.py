"""Open terminals: every curved stroke end in letters and figures (c e s a g j
2 3 5 C G J S, с е з э ...) is cut square to the stroke, as in Akzidenz
Grotesk, instead of horizontally or vertically. The angle therefore follows
each letter's own curve, and the apertures open up a little.

How: at a terminal, the stroke's direction is taken from the tangents of its
inner and outer edges; the corner that runs ahead along that direction slides
back along its own edge (the quadratic it sits on is split there, de
Casteljau) until the cap is perpendicular to the stroke. Only points move --
no boolean ops -- so outlines keep their structure across weights. Where the
next on-curve point is implied it is made explicit first.

    python3 chisel.py out             # statics: terminals found per font
    python3 chisel.py out --variable  # masters: terminals found once, on the
                                      # Regular master, cut the same way in all

Only open ends of curved strokes on outer contours are touched: square ends
of straight strokes (serifs, crossbars, stem feet), joins (ю's bar into its
bowl) and counters stay as they are. Super/subscripts are left alone.
"""
import sys, glob, math, os, unicodedata
import pathops
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph

VARIABLE = "--variable" in sys.argv
MAX_CUT = 1.0          # never slide a corner further than one stem
MIN_ANGLE = 6          # caps already within this many degrees of square stay
SHARP = float(sys.argv[sys.argv.index("--sharp") + 1]) if "--sharp" in sys.argv else 20.0
                       # cut this many degrees past square: a sharper tip
# --beak DEPTH [CURVE]: display terminals (SB Sans Display-like). The inner
# corner slides DEPTH stems back along the inner edge and the cut bows into the
# stroke by CURVE x its length, leaving a sharp, slightly hooked tip.
BEAK = float(sys.argv[sys.argv.index("--beak") + 1]) if "--beak" in sys.argv else 0.0
CURVE = float(sys.argv[sys.argv.index("--beak") + 2]) if "--beak" in sys.argv and len(sys.argv) > sys.argv.index("--beak") + 2 and not sys.argv[sys.argv.index("--beak") + 2].startswith("--") else 0.18


def stem(f):
    p = skPathFromGlyph(f.getBestCmap()[ord("n")], f.getGlyphSet())
    b = pathops.Path(); b.moveTo(-500, 199.5); b.lineTo(1500, 199.5); b.lineTo(1500, 200.5); b.lineTo(-500, 200.5); b.close()
    s = pathops.op(p, b, pathops.PathOp.INTERSECTION, fix_winding=True)
    r = sorted((c.bounds[0], c.bounds[2]) for c in s.contours)
    return r[0][1] - r[0][0]


def contours(g):
    out, s = [], 0
    for e in g.endPtsOfContours:
        out.append(list(range(s, e + 1))); s = e + 1
    return out


def find_caps(f, name, t):
    """[(contour index, position of the cap's first point in that contour)]"""
    g = f["glyf"][name]
    if g.isComposite() or g.numberOfContours <= 0:
        return []
    pts, fl = list(g.coordinates), list(g.flags)
    ink = skPathFromGlyph(name, f.getGlyphSet())

    def inked(x, y):
        b = pathops.Path(); b.moveTo(x - 2, y - 2); b.lineTo(x + 2, y - 2); b.lineTo(x + 2, y + 2); b.lineTo(x - 2, y + 2); b.close()
        return pathops.op(ink, b, pathops.PathOp.INTERSECTION, fix_winding=True).area > 1

    caps = []
    for ci, idx in enumerate(contours(g)):
        n = len(idx)
        area = sum(pts[idx[m]][0] * pts[idx[(m + 1) % n]][1] - pts[idx[(m + 1) % n]][0] * pts[idx[m]][1] for m in range(n))
        if area > 0:
            continue                                        # a counter
        for k in range(n):
            i, j = idx[k], idx[(k + 1) % n]
            if not (fl[i] & 1 and fl[j] & 1):
                continue
            (x0, y0), (x1, y1) = pts[i], pts[j]
            L = math.hypot(x1 - x0, y1 - y0)
            if not (0.55 * t <= L <= 1.6 * t):
                continue
            p, q = pts[idx[(k - 1) % n]], pts[idx[(k + 2) % n]]
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            a, b = (p[0] - x0, p[1] - y0), (q[0] - x1, q[1] - y1)
            la, lb = math.hypot(*a) or 1, math.hypot(*b) or 1
            if not (abs(a[0] * ux + a[1] * uy) / la < 0.45 and abs(b[0] * ux + b[1] * uy) / lb < 0.45
                    and (a[0] * b[0] + a[1] * b[1]) / (la * lb) > 0.6):
                continue                                    # not the end of a stroke
            if fl[idx[(k - 1) % n]] & 1 and fl[idx[(k + 2) % n]] & 1:
                continue                                    # a straight stroke: keep it square
            ox_, oy_ = -(a[0] / la + b[0] / lb), -(a[1] / la + b[1] / lb)
            lo = math.hypot(ox_, oy_) or 1
            if inked((x0 + x1) / 2 + ox_ / lo * t * 0.12, (y0 + y1) / 2 + oy_ / lo * t * 0.12):
                continue                                    # a join, not an open end
            caps.append((ci, k))
    return caps


def quad_point(p0, p1, p2, s):
    return ((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0],
            (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1])


def unit(x, y):
    L = math.hypot(x, y) or 1
    return x / L, y / L


def apply_caps(g, caps, t, decide=None, record=None):
    """decide: {(ci, k): (kk is the cap's first point, skip, snap)} forced choices;
    record: dict filled with the choices made here (for the variable masters)."""
    pts = [tuple(map(float, p)) for p in g.coordinates]
    fl = list(g.flags)
    new_pts, new_fl, ends = [], [], []
    for ci, idx in enumerate(contours(g)):
        P = [pts[i] for i in idx]; F = [fl[i] for i in idx]
        for k in sorted((k for c, k in caps if c == ci), reverse=True):
            n = len(P); A, B = P[k], P[(k + 1) % n]
            # stroke direction towards the tip: against the edges leaving the cap
            ta = unit(P[(k - 1) % n][0] - A[0], P[(k - 1) % n][1] - A[1])
            tb = unit(P[(k + 2) % n][0] - B[0], P[(k + 2) % n][1] - B[1])
            u = unit(-(ta[0] + tb[0]), -(ta[1] + tb[1]))
            cap = unit(B[0] - A[0], B[1] - A[1])
            square = abs(cap[0] * u[0] + cap[1] * u[1]) < math.sin(math.radians(MIN_ANGLE))
            skip = square and not BEAK and not SHARP          # already square to the stroke
            if decide is not None and (ci, k) in decide:
                skip = decide[(ci, k)][1]
            if skip:
                if record is not None: record[(ci, k)] = (None, True, False)
                continue
            # the corner further along u is cut back to the other one's level
            if (A[0] - B[0]) * u[0] + (A[1] - B[1]) * u[1] > 0:
                kk, dr, other = k, -1, B
            else:
                kk, dr, other = (k + 1) % n, +1, A
            if square and SHARP and not BEAK:
                # a square cap: cut the outer corner, which opens the aperture
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                gcx, gcy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                horiz = abs(A[1] - B[1]) < abs(A[0] - B[0])
                da = abs(A[0] - gcx) if horiz else abs(A[1] - gcy)
                db = abs(B[0] - gcx) if horiz else abs(B[1] - gcy)
                kk, dr, other = (k, -1, B) if da > db else ((k + 1) % n, +1, A)
            if BEAK:
                # display: always the inner corner (nearer the glyph centre, along the cap)
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                gcx, gcy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
                horiz = abs(A[1] - B[1]) < abs(A[0] - B[0])
                da = abs(A[0] - gcx) if horiz else abs(A[1] - gcy)
                db = abs(B[0] - gcx) if horiz else abs(B[1] - gcy)
                kk, dr, other = (k, -1, B) if da < db else ((k + 1) % n, +1, A)
            if decide is not None and (ci, k) in decide and decide[(ci, k)][0] is not None:
                kk, dr, other = (k, -1, B) if decide[(ci, k)][0] else ((k + 1) % n, +1, A)
            first = kk == k
            capw = math.hypot(B[0] - A[0], B[1] - A[1])
            level = other[0] * u[0] + other[1] * u[1] - capw * math.tan(math.radians(SHARP))
            ahead = lambda q: q[0] * u[0] + q[1] * u[1] - level
            k1, k2 = (kk + dr) % n, (kk + 2 * dr) % n
            if F[k1] & 1:                                   # straight edge behind the corner
                p0, p1 = P[kk], P[k1]
                d0, d1 = ahead(p0), ahead(p1)
                if record is not None:
                    record[(ci, k)] = (first, False, False)
                if d0 - d1 <= 0:
                    continue
                s = min(d0 / (d0 - d1), MAX_CUT * t / (math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1), 0.85)
                P[kk] = (p0[0] + (p1[0] - p0[0]) * s, p0[1] + (p1[1] - p0[1]) * s)
                continue
            if not (F[k2] & 1):                             # make the implied on-curve point explicit
                mid = ((P[k1][0] + P[k2][0]) / 2, (P[k1][1] + P[k2][1]) / 2)
                at = k2 if dr == 1 else k1
                if dr == 1 and k2 == 0:
                    at = n
                P.insert(at, mid); F.insert(at, 1)
                if at <= kk:
                    kk += 1
                n = len(P); k1, k2 = (kk + dr) % n, (kk + 2 * dr) % n
            p0, p1, p2 = P[kk], P[k1], P[k2]
            # first parameter where the curve has come back to the other corner's level
            # (display beaks: where it has run BEAK stems back)
            s_hit, acc, prev = None, 0.0, p0
            for m in range(1, 401):
                s = m / 400; q = quad_point(p0, p1, p2, s)
                acc += math.hypot(q[0] - prev[0], q[1] - prev[1]); prev = q
                if BEAK and acc >= BEAK * t:
                    s_hit = s; break
                if not BEAK and (acc > MAX_CUT * t or ahead(q) <= 0):
                    s_hit = s; break
            s_hit = min(s_hit if s_hit is not None else 0.85, 0.85)
            q = quad_point(p0, p1, p2, s_hit)
            # a cut that ends a few units short of the next on-curve point would
            # leave a stub of a curve that rounding to integers bends; end the
            # cut on that point instead and drop the stub
            snap = math.hypot(q[0] - p2[0], q[1] - p2[1]) < max(10.0, 0.1 * t)
            if kk < k - 1 or k1 < k - 1:                  # wraps past the contour start:
                snap = False                                # deleting there would shift the caps still to do
            if decide is not None and (ci, k) in decide and len(decide[(ci, k)]) > 2:
                snap = decide[(ci, k)][2]
            if record is not None:
                record[(ci, k)] = (first, False, snap)
            if snap:
                P = [q_ for m, q_ in enumerate(P) if m not in (kk, k1)]
                F = [f_ for m, f_ in enumerate(F) if m not in (kk, k1)]
                continue
            P[kk] = q
            P[k1] = ((1 - s_hit) * p1[0] + s_hit * p2[0], (1 - s_hit) * p1[1] + s_hit * p2[1])
            if BEAK and CURVE:
                # bow the cut into the stroke: one off-curve point between the two cap ends
                c0, c1 = P[kk], other
                mx, my = (c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2
                L = math.hypot(c1[0] - c0[0], c1[1] - c0[1])
                nx, ny = -(c1[1] - c0[1]) / (L or 1), (c1[0] - c0[0]) / (L or 1)
                if nx * -u[0] + ny * -u[1] < 0:
                    nx, ny = -nx, -ny
                ctrl = (mx + nx * CURVE * L, my + ny * CURVE * L)
                n = len(P)
                at = (kk + 1) if dr == -1 else kk           # between kk and the other cap end
                P.insert(at, ctrl); F.insert(at, 0)
        new_pts += P; new_fl += F; ends.append(len(new_pts) - 1)
    g.coordinates = type(g.coordinates)([(round(x), round(y)) for x, y in new_pts])
    g.flags = type(g.flags)(new_fl) if not isinstance(g.flags, list) else new_fl
    g.endPtsOfContours = ends


def targets(f):
    """Letters and decimal figures (and their alternates); not super/subscripts."""
    cmap = f.getBestCmap(); rev = {}
    for u, n in cmap.items():
        rev.setdefault(n, u)
    out = []
    for n in f.getGlyphOrder():
        u = rev.get(n) or rev.get(n.split(".")[0])
        if u is not None and (unicodedata.category(chr(u))[0] == "L" or unicodedata.category(chr(u)) == "Nd"):
            out.append(n)
    return out


def ink(f, name):
    """(area, number of contours) of the glyph with its overlaps removed."""
    clean = pathops.simplify(skPathFromGlyph(name, f.getGlyphSet()), fix_winding=True)
    return abs(clean.area), len(list(clean.contours))


def sane(f, name, before, before_contours):
    """Guard against a broken cut: same contours, no ink gained, at most 12%
    taken, and no contour crossing itself or another -- a crossing would
    change how many contours remain once the overlaps are removed."""
    if f["glyf"][name].numberOfContours != before_contours:
        return False
    area, parts = ink(f, name)
    return parts == before[1] and before[0] * 0.88 <= area <= before[0] + 2


paths = sorted(glob.glob(os.path.join(sys.argv[1], "PaperMonoCyr-*.ttf")))
fonts = {p: TTFont(p) for p in paths}
plan, choices = {}, {}
if VARIABLE:
    import copy
    ref = next(f for p, f in fonts.items() if p.endswith("-Regular.ttf"))
    tr = stem(ref)
    for n in targets(ref):
        caps = find_caps(ref, n, tr)
        if caps:
            rec = {}
            apply_caps(copy.deepcopy(ref["glyf"][n]), caps, tr, record=rec)
            plan[n], choices[n] = caps, rec
reverted_all = set()
for p, f in fonts.items():
    t = stem(f); done = 0; reverted = []
    for n in targets(f):
        caps = plan.get(n, []) if VARIABLE else find_caps(f, n, t)
        if not caps:
            continue
        g = f["glyf"][n]
        before = (list(g.coordinates), bytearray(g.flags), list(g.endPtsOfContours))
        ink0, nc0 = ink(f, n), g.numberOfContours
        apply_caps(g, caps, t, decide=choices.get(n) if VARIABLE else None)
        g.recalcBounds(f["glyf"])
        if not sane(f, n, ink0, nc0):
            g.coordinates = type(g.coordinates)(before[0]); g.flags = type(g.flags)(before[1])
            g.endPtsOfContours = before[2]; g.recalcBounds(f["glyf"])
            reverted.append(n); reverted_all.add(n)
            continue
        f["hmtx"][n] = (f["hmtx"][n][0], getattr(g, "xMin", 0))
        done += 1
    f.save(p)
    print(os.path.basename(p), "terminals opened in", done, "glyphs", f"| reverted by the guard: {reverted}" if reverted else "")
if VARIABLE and reverted_all:
    # a glyph reverted in one master but cut in another would break the variable font
    raise SystemExit(f"chisel: the guard reverted {sorted(reverted_all)} in some master; fix before building the variable font")
