"""Stroke contrast with a humanist (broad-nib) axis.

Every point of the outline moves along its normal by an amount that depends
on the direction of that normal, d(theta) = A + B*cos(2*(theta - AXIS)).
With the axis tilted 30 degrees this is a broad pen held at 30 degrees:
verticals and descending diagonals (\\) get a little heavier, horizontals and
ascending diagonals (/) thinner, and the stress of round letters leans back,
thin at 11 and 5 o'clock.

The offset curve is sampled exactly (every segment, at its own normals) and
the original points are fitted to those samples by least squares, with the
curve energy in the fit (Gauss-Newton): at every smooth join the jump in
curvature must shrink to CALM of the original one, and each curve keeps the
curvature an exact offset would have. So the contrast flows round a bowl
with fewer kinks than the source had. Corners keep their exact mitre;
extrema keep their horizontal or vertical handles (tied into the fit, not
forced after). No point is added or removed, so the variable masters stay
compatible.

Thinning moves the outer horizontals off the baseline and x-height, so y is
then remapped: everything below the baseline drops back by the same amount,
everything above the x-height rises back, and the space between stretches
to fit. Dots keep their shape and only follow that remap.

Applies to letters, figures, punctuation, currency and math signs, and the
code ligatures built from them; box drawing, blocks, symbols and marks stay
as they are. Usage: contrast.py DIR [--variable]"""
import sys, os, glob, math, unicodedata
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph
import pathops

AXIS = math.radians(30)        # tilt of the stress, from vertical stems
VERT = 0.024                   # stems: extra thickness per side, x stem
HORZ = 0.090                   # horizontals: thinner per side, x stem
ENERGY = 0.02                  # weight of the bending energy of the displacement
FAIR = 6000.0                  # weight of curvature continuity at smooth joins (units x radius)
CALM = 0.18                    # curvature jumps aim at this share of the original ones
PROFILE = 300.0                # weight of following the offset curve's own curvature
SAMPLES = 10                   # samples per curve segment
CORNER = math.radians(12)      # a turn sharper than this is a corner
CATS = {"Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Po", "Pd", "Ps", "Pe", "Pi", "Pf", "Pc", "Sc", "Sm"}
SKIP = [(0x2190, 0x21FF), (0x2500, 0x25FF), (0x2800, 0x28FF), (0xE000, 0xF8FF), (0x2300, 0x23FF)]


def stem(f):
    p = skPathFromGlyph(f.getBestCmap()[ord("n")], f.getGlyphSet())
    b = pathops.Path(); b.moveTo(-500, 199.5); b.lineTo(1500, 199.5); b.lineTo(1500, 200.5); b.lineTo(-500, 200.5); b.close()
    s = pathops.op(p, b, pathops.PathOp.INTERSECTION, fix_winding=True)
    r = sorted((c.bounds[0], c.bounds[2]) for c in s.contours)
    return r[0][1] - r[0][0]


def targets(f):
    cmap = f.getBestCmap(); rev = {}
    for u, n in cmap.items():
        rev.setdefault(n, u)
    def ok(u):
        return unicodedata.category(chr(u)) in CATS and not any(a <= u <= b for a, b in SKIP)
    out = {}                                       # name -> True for letters and figures
    for n in f.getGlyphOrder():
        if n.endswith(".liga"):
            out[n] = False; continue
        u = rev.get(n) or rev.get(n.split(".")[0])
        if u is not None and ok(u) and not n.split(".")[-1] in ("numr", "dnom"):
            out[n] = unicodedata.category(chr(u))[0] == "L" or unicodedata.category(chr(u)) == "Nd"
    return out


def unit(x, y):
    L = math.hypot(x, y)
    return (x / L, y / L) if L > 1e-9 else (0.0, 0.0)


def segments(P, on):
    """The contour as line and quadratic segments over 'nodes'; a node is a
    dict {point index: weight} (an implied on-curve point is the mean of two
    off-curve points). Returns [(nodes...)] with 2 nodes for a line, 3 for a quad."""
    n = len(P); nodes = []
    for i in range(n):
        p = (i - 1) % n
        if not on[i] and not on[p]:
            nodes.append(({p: 0.5, i: 0.5}, True))
        nodes.append(({i: 1.0}, on[i]))
    k0 = next(k for k, (_, o) in enumerate(nodes) if o)
    nodes = nodes[k0:] + nodes[:k0]
    segs, k, m = [], 0, len(nodes)
    while k < m:
        a = nodes[k][0]; b, bon = nodes[(k + 1) % m]
        if bon:
            segs.append((a, b)); k += 1
        else:
            segs.append((a, b, nodes[(k + 2) % m][0])); k += 2
    return segs


def at(seg, X, u):
    """Position, tangent and coefficient row of a segment at parameter u."""
    pos = lambda c: sum(w * X[i] for i, w in c.items())
    if len(seg) == 2:
        a, b = seg; wa, wb = 1 - u, u
        tan = pos(b) - pos(a); coef = {}
        for c, w in ((a, wa), (b, wb)):
            for i, v in c.items():
                coef[i] = coef.get(i, 0) + v * w
    else:
        a, b, c_ = seg; wa, wb, wc = (1 - u) ** 2, 2 * u * (1 - u), u * u
        tan = 2 * (1 - u) * (pos(b) - pos(a)) + 2 * u * (pos(c_) - pos(b)); coef = {}
        for c, w in ((a, wa), (b, wb), (c_, wc)):
            for i, v in c.items():
                coef[i] = coef.get(i, 0) + v * w
    return sum(w * X[i] for i, w in coef.items()), tan, coef


def kappa(seg, X, u):
    """Signed curvature of a segment at u (0 for a line)."""
    if len(seg) == 2:
        return 0.0
    pos = lambda c: sum(w * X[i] for i, w in c.items())
    p0, p1, p2 = (pos(c) for c in seg)
    d1 = 2 * (1 - u) * (p1 - p0) + 2 * u * (p2 - p1); d2 = 2 * (p2 - 2 * p1 + p0)
    v = math.hypot(d1[0], d1[1])
    return float(d1[0] * d2[1] - d1[1] * d2[0]) / v ** 3 if v > 1e-6 else 0.0


def contrast(f):
    t = stem(f)
    dv, dh = VERT * t, -HORZ * t
    xh = f["OS/2"].sxHeight

    def pen(axis):
        """d(theta) with d(0) = dv for vertical stems, d(90) = dh for horizontals."""
        c0, c90 = math.cos(2 * axis), math.cos(2 * (math.pi / 2 - axis))
        B = (dv - dh) / (c0 - c90); A = dv - B * c0
        return lambda nx, ny: A + B * math.cos(2 * (math.atan2(ny, nx) - axis)), -(A + B * c90)

    # letters and figures get the tilted pen; signs, brackets and the code
    # ligatures an upright one, so < >, ( ), -> <- stay mirror images
    d_letter, shift = pen(AXIS)
    d_sign, _ = pen(0.0)
    d = d_letter

    def remap(y):
        if y <= shift:
            return y - shift
        if y >= xh - shift:
            return y + shift
        return (y - shift) * xh / (xh - 2 * shift)

    def moved(p, nrm, dd=None):
        q = p + (d(*nrm) if dd is None else dd) * np.array(nrm)
        return np.array([q[0], remap(q[1])])

    def mitre(p, n1, n2, d1=None, d2=None):
        """Corner p between edges with normals n1, n2: where the two moved
        edges meet (n1.v = d1, n2.v = d2), then remapped."""
        d1 = d(*n1) if d1 is None else d1
        d2 = d(*n2) if d2 is None else d2
        det = n1[0] * n2[1] - n1[1] * n2[0]
        if abs(det) < 0.05:                                  # a hairpin: the edges barely meet
            vx, vy = (d1 * n1[0] + d2 * n2[0]) / 2, (d1 * n1[1] + d2 * n2[1]) / 2
        else:
            vx = (d1 * n2[1] - d2 * n1[1]) / det
            vy = (n1[0] * d2 - n2[0] * d1) / det
        lim = 3 * max(abs(d1), abs(d2)) + 1; L = math.hypot(vx, vy)
        if L > lim:
            vx, vy = vx * lim / L, vy * lim / L
        return np.array([p[0] + vx, remap(p[1] + vy)])

    glyf = f["glyf"]; done = 0
    for name, letter in targets(f).items():
        d = d_letter if letter else d_sign
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        coords = np.array(g.coordinates, float); flags = list(g.flags)
        new = coords.copy(); start = 0
        for end in g.endPtsOfContours:
            idx = list(range(start, end + 1)); start = end + 1
            P = coords[idx]; on = [bool(flags[i] & 1) for i in idx]; n = len(idx)
            w, h = np.ptp(P[:, 0]), np.ptp(P[:, 1])
            area = sum(P[k - 1, 0] * P[k, 1] - P[k, 0] * P[k - 1, 1] for k in range(n)) / 2
            if area < 0 and w < 2.2 * t and h < 2.2 * t and 0.6 < w / max(h, 1) < 1.6:
                continue                                     # a dot (outer, small, round): as it is
            if min(w, h) < 0.5 * t:
                continue                                     # a sliver joining parts: thinning would turn it inside out
            new[idx] = fit(P, on, n, moved, mitre, d, t)
        g.coordinates = type(g.coordinates)([(int(round(x)), int(round(y))) for x, y in new])
        g.recalcBounds(glyf)
        f["hmtx"][name] = (f["hmtx"][name][0], getattr(g, "xMin", 0))
        done += 1
    return done, round(dv, 1), round(dh, 1)


def fit(P, on, n, moved, mitre, d, t):
    segs = segments(P, on)
    rows, rhs, wts = [], [], []

    def target(coef, q, wt):
        rows.append(coef); rhs.append(q); wts.append(wt)

    # tangents into and out of every on-curve point, to tell corners from smooth points
    tin, tout = {}, {}
    for seg in segs:
        a, z = seg[0], seg[-1]
        _, t0, _ = at(seg, P, 0.0); _, t1, _ = at(seg, P, 1.0)
        if len(a) == 1: tout[next(iter(a))] = unit(*t0)
        if len(z) == 1: tin[next(iter(z))] = unit(*t1)
    # the cut end of a curved stroke (c e s a ...) is no horizontal: it stays
    # where it is (only following the remap), or thinning would pull it in
    # and wind the curve before it tighter
    cap_out, cap_in, capseg = set(), set(), set()
    for k, seg in enumerate(segs):
        if len(seg) != 2 or len(seg[0]) != 1 or len(seg[1]) != 1:
            continue
        i, j = next(iter(seg[0])), next(iter(seg[1]))
        L = float(np.linalg.norm(P[j] - P[i]))
        if not (0.4 * t <= L <= 1.8 * t) or i not in tin or j not in tout:
            continue
        u = (P[j] - P[i]) / L; a, b = tin[i], tout[j]
        curved = len(segs[k - 1]) == 3 or len(segs[(k + 1) % len(segs)]) == 3
        # square ends and the slanted cuts of chisel.py (which runs first) alike
        if curved and abs(a[0] * u[0] + a[1] * u[1]) < 0.75 and abs(b[0] * u[0] + b[1] * u[1]) < 0.75                 and a[0] * b[0] + a[1] * b[1] < -0.6:
            cap_out.add(i); cap_in.add(j); capseg.add(k)
    corner = set()
    for i in range(n):
        if on[i] and i in tin and i in tout:
            a, b = tin[i], tout[i]
            if math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1]))) > CORNER:
                corner.add(i)
                target({i: 1.0}, mitre(P[i], (-a[1], a[0]), (-b[1], b[0]),
                                       0.0 if i in cap_in else None, 0.0 if i in cap_out else None), 200.0)
            else:
                nr = unit(-(a[1] + b[1]), a[0] + b[0])
                target({i: 1.0}, moved(P[i], nr), 6.0)
    # samples along every segment, at the exact normal there
    for sk, seg in enumerate(segs):
        for k in range(SAMPLES):
            u = (k + 0.5) / SAMPLES
            p, tn, coef = at(seg, P, u)
            tx, ty = unit(*tn)
            target(coef, moved(p, (-ty, tx), 0.0 if sk in capseg else None), 1.0)
    # extrema keep flat handles: the handles share that coordinate with their
    # point, built into the fit as one unknown (per axis) rather than forced after
    # (an implied extremum, between two off-curve handles level with each
    # other, ties those two the same way)
    root = [list(range(n)), list(range(n))]

    def find(ax, i):
        while root[ax][i] != i:
            root[ax][i] = root[ax][root[ax][i]]; i = root[ax][i]
        return i

    def join(ax, i, j):
        root[ax][find(ax, i)] = find(ax, j)

    for i in range(n):
        a, c = (i - 1) % n, (i + 1) % n
        if on[i] and i not in corner:
            for ax in (1, 0):
                if abs(P[a, ax] - P[i, ax]) < 0.6 and abs(P[c, ax] - P[i, ax]) < 0.6:
                    join(ax, a, i); join(ax, c, i)
                    break
        elif not on[i] and not on[c]:
            for ax in (1, 0):
                if abs(P[c, ax] - P[i, ax]) < 0.6:
                    join(ax, c, i)
                    break
    tie = [[find(ax, i) for i in range(n)] for ax in (0, 1)]  # x, y: point -> unknown
    # least squares with the bending energy of the displacement D = X - P
    M = np.zeros((len(rows), n)); T = np.array(rhs); Wt = np.sqrt(np.array(wts))
    for r, coef in enumerate(rows):
        for i, v in coef.items():
            M[r, i] += v
    E = []
    for i in range(n):
        if i in corner:
            continue
        row = np.zeros(n); row[(i - 1) % n] += 1; row[i] -= 2; row[(i + 1) % n] += 1
        E.append(row)
    E = np.array(E) if E else np.zeros((0, n))
    # unknowns: one per tied group and axis; X(z) = P + [Gx zx, Gy zy]
    G = []
    for ax in (0, 1):
        keys = sorted(set(tie[ax])); col = {k: j for j, k in enumerate(keys)}
        Ga = np.zeros((n, len(keys)))
        for i in range(n):
            Ga[i, col[tie[ax][i]]] = 1
        G.append(Ga)
    nx_ = G[0].shape[1]

    def X_of(z):
        return P + np.stack([G[0] @ z[:nx_], G[1] @ z[nx_:]], axis=1)

    # linear part: offset samples and the bending energy, for both axes at once
    Lx = np.vstack([(M @ G[0]) * Wt[:, None], math.sqrt(ENERGY) * (E @ G[0])])
    Ly = np.vstack([(M @ G[1]) * Wt[:, None], math.sqrt(ENERGY) * (E @ G[1])])
    lin = np.block([[Lx, np.zeros((Lx.shape[0], Ly.shape[1]))], [np.zeros((Ly.shape[0], Lx.shape[1])), Ly]])
    rlin = np.concatenate([(T[:, 0] - M @ P[:, 0]) * Wt, np.zeros(len(E)), (T[:, 1] - M @ P[:, 1]) * Wt, np.zeros(len(E))])
    z = np.linalg.lstsq(lin, rlin, rcond=None)[0]

    # curve energy: smooth joins between segments keep (CALM x) their curvature jump
    joins = []
    for A_, B_ in zip(segs, segs[1:] + segs[:1]):
        if len(A_) == 2 and len(B_) == 2:
            continue
        _, ta, _ = at(A_, P, 1.0); _, tb, _ = at(B_, P, 0.0)
        ta, tb = unit(*ta), unit(*tb)
        if ta[0] * tb[0] + ta[1] * tb[1] > math.cos(CORNER):
            joins.append((A_, B_))

    # ... and every curve keeps the curvature an exact offset would have,
    # k' = k / (1 - k d), at its ends and middle
    prof = []
    for seg in segs:
        if len(seg) == 3:
            for u in (0.0, 0.5, 1.0):
                _, tn, _ = at(seg, P, u); tx, ty = unit(*tn)
                k0 = kappa(seg, P, u); dd = d(-ty, tx)
                k1 = k0 / (1 - k0 * dd) if abs(1 - k0 * dd) > 0.2 else k0
                # a tight turn would get tighter still; let it sharpen by a quarter at most
                prof.append((seg, u, max(-1.25 * abs(k0), min(1.25 * abs(k0), k1))))

    def res(X):
        r1 = [FAIR * (kappa(A_, X, 1.0) - kappa(B_, X, 0.0)) for A_, B_ in joins]
        r2 = [PROFILE * kappa(seg, X, u) for seg, u, _ in prof]
        return np.array(r1 + r2)

    if joins or prof:
        goal = np.array([FAIR * CALM * (kappa(A_, P, 1.0) - kappa(B_, P, 0.0)) for A_, B_ in joins]
                        + [PROFILE * k for _, _, k in prof])
        for _ in range(4):
            X = X_of(z); j0 = res(X)
            J = np.zeros((len(j0), len(z)))
            for v in range(len(z)):
                dz = np.zeros(len(z)); dz[v] = 0.05
                J[:, v] = (res(X_of(z + dz)) - j0) / 0.05
            # minimise |lin z - rlin|^2 + |j0 + J (z' - z) - goal|^2
            Aall = np.vstack([lin, J])
            ball = np.concatenate([rlin, goal - j0 + J @ z])
            z = np.linalg.lstsq(Aall, ball, rcond=None)[0]
    X = X_of(z)
    # smooth points between two handles stay on the line of their handles
    for i in range(n):
        if not on[i] or i in corner:
            continue
        a, c = (i - 1) % n, (i + 1) % n
        flat = any(tie[ax][a] == tie[ax][i] == tie[ax][c] for ax in (0, 1))
        if not flat and not on[a] and not on[c]:
            la, lc = np.linalg.norm(P[i] - P[a]), np.linalg.norm(P[c] - P[i])
            if la + lc > 0:
                X[i] = X[a] + (X[c] - X[a]) * la / (la + lc)
    return X


if __name__ == "__main__":
    for p in sorted(glob.glob(os.path.join(sys.argv[1], "PaperMonoCyr-*.ttf"))):
        f = TTFont(p)
        done, dv, dh = contrast(f)
        f.save(p)
        print(os.path.basename(p), "contrast in", done, "glyphs | stems", f"+{dv}", "horizontals", dh, "per side")
