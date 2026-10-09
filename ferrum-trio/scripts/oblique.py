"""Italic (oblique) styles from the finished upright TTFs, in place.

    python3 oblique.py ../fonts/ttf

For every upright FamilyName-Weight.ttf in the folder this writes
FamilyName-WeightItalic.ttf (Regular -> Italic), autohinted.

- Slant 10° (Geist Mono Italic uses 12°, JetBrains Mono ~9°; in a 606-unit
  cell 10° keeps ascenders and capitals from leaning out of the cell).
- The shear pivots at half the x-height, so lowercase stays centred in its
  cell; advance widths are untouched (606 / 303 / 909).
- Shearing keeps horizontal run widths, so a stroke's perpendicular thickness
  changes with its slope (stems -1.5%, "/" strokes thinner, "\\" thicker).
  Every edge is moved along its normal to give each stroke its upright
  thickness back.
- Box drawing, block elements and private-use symbols (Powerline / Nerd
  icons) stay upright so they still tile.
- Mark anchors follow the shear; italic angle, caret slope, fsSelection,
  macStyle and the name table are set for Regular/Italic, Bold/Bold Italic
  style linking.
- Every font in the folder, upright and italic, gets a STAT table (weight +
  italic axes) so the uprights and italics are seen as one family.
"""
import sys, os, glob, math, subprocess
import pathops
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont
from fontTools.ttLib.removeOverlaps import skPathFromGlyph, ttfGlyphFromSkPath
from fontTools import subset

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ANGLE = 10.0
TAN = math.tan(math.radians(ANGLE))
XH = 509
PIVOT = XH / 2
UPRIGHT = [(0x2500, 0x259F), (0xE000, 0xF8FF), (0xF0000, 0x10FFFF)]


def unhinted(path):
    """Drop the upright's hints and ttfautohint's marker glyph."""
    f = TTFont(path)
    o = subset.Options()
    o.hinting = False; o.layout_features = ["*"]; o.name_IDs = ["*"]; o.name_languages = ["*"]
    o.name_legacy = True; o.glyph_names = True; o.notdef_outline = True; o.legacy_kern = True
    o.drop_tables = []; o.passthrough_tables = True; o.recalc_bounds = True
    s = subset.Subsetter(o)
    s.populate(glyphs=[g for g in f.getGlyphOrder() if g != ".ttfautohint"], unicodes=f.getBestCmap().keys())
    s.subset(f)
    return f


def runs(path, y):
    b = pathops.Path(); b.moveTo(-2000, y - 0.5); b.lineTo(3000, y - 0.5); b.lineTo(3000, y + 0.5); b.lineTo(-2000, y + 0.5); b.close()
    s = pathops.op(path, b, pathops.PathOp.INTERSECTION, fix_winding=True)
    return sorted((c.bounds[0], c.bounds[2]) for c in s.contours)


def compensate(glyph, p_ref):
    """The glyph is already sheared. Move every edge along its normal by half
    the thickness the shear took from (or added to) a stroke of
    perpendicular thickness p_ref at that slope; vertices go to the
    intersection of their two moved edges."""
    pts = [tuple(map(float, q)) for q in glyph.coordinates]
    out = list(pts); start = 0

    def edge(a, b):
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty)
        if L < 1e-6:
            return None
        n = (-ty / L, tx / L)                       # outward for a clockwise contour
        s_now = abs(ty) / L                         # sin of the sheared edge's angle
        if s_now < 0.05:
            return n, 0.0
        # the edge before the shear: direction (tx - ty*TAN, ty)
        ox = tx - ty * TAN
        s_was = abs(ty) / math.hypot(ox, ty)
        return n, p_ref / 2 * (1 - s_now / s_was)

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
            if abs(det) < 0.5:                      # sharp or flat joins: plain offset
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


def shear_x(x, y):
    return x + (y - PIVOT) * TAN


def upright_glyphs(f):
    keep = set()
    for u, g in f.getBestCmap().items():
        if any(a <= u <= b for a, b in UPRIGHT):
            keep.add(g)
    return keep


def build(src, dst):
    f = unhinted(src)
    glyf = f["glyf"]
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    keep = upright_glyphs(f)

    def stem(ch, y):
        r = runs(skPathFromGlyph(cmap[ord(ch)], gs), y)
        return r[0][1] - r[0][0]
    n_stem, H_stem = stem("n", 200), stem("H", 200)

    # all outlines first (composites decomposed), then rewrite
    paths, upright = {}, {}
    for name in f.getGlyphOrder():
        g = glyf[name]
        if name in keep:
            if g.isComposite():
                upright[name] = skPathFromGlyph(name, gs)
            continue
        if g.numberOfContours == 0:
            continue
        paths[name] = skPathFromGlyph(name, gs)
    for name, p in paths.items():
        if p.bounds == (0, 0, 0, 0):
            continue
        g = ttfGlyphFromSkPath(pathops.simplify(p, fix_winding=True, clockwise=True))
        g.coordinates = type(g.coordinates)([(shear_x(x, y), y) for x, y in g.coordinates])
        g.recalcBounds(glyf)
        compensate(g, H_stem if getattr(g, "yMax", 0) > XH + 60 else n_stem)
        glyf[name] = g
        g.recalcBounds(glyf)
        f["hmtx"][name] = (f["hmtx"][name][0], getattr(g, "xMin", 0))
    # upright glyphs that were composites of slanted parts: decompose them upright
    for name, p in upright.items():
        if True:
            ng = ttfGlyphFromSkPath(pathops.simplify(p, fix_winding=True, clockwise=True))
            glyf[name] = ng; ng.recalcBounds(glyf)
            f["hmtx"][name] = (f["hmtx"][name][0], getattr(ng, "xMin", 0))

    # anchors follow the shear
    for tag in ("GPOS",):
        for lk in f[tag].table.LookupList.Lookup:
            for st in lk.SubTable:
                kind = type(st).__name__
                anchors = []
                if kind == "MarkBasePos":
                    anchors += [a for r in st.BaseArray.BaseRecord for a in r.BaseAnchor]
                    anchors += [r.MarkAnchor for r in st.MarkArray.MarkRecord]
                elif kind == "MarkMarkPos":
                    anchors += [a for r in st.Mark2Array.Mark2Record for a in r.Mark2Anchor]
                    anchors += [r.MarkAnchor for r in st.Mark1Array.MarkRecord]
                elif kind == "MarkLigPos":
                    for la in st.LigatureArray.LigatureAttach:
                        anchors += [a for cr in la.ComponentRecord for a in cr.LigatureAnchor]
                    anchors += [r.MarkAnchor for r in st.MarkArray.MarkRecord]
                for a in anchors:
                    if a is not None:
                        a.XCoordinate = round(shear_x(a.XCoordinate, a.YCoordinate))

    # metadata
    f["post"].italicAngle = -ANGLE
    f["hhea"].caretSlopeRise = 1000
    f["hhea"].caretSlopeRun = round(1000 * TAN)
    f["hhea"].caretOffset = 0
    os2 = f["OS/2"]
    bold = bool(os2.fsSelection & (1 << 5))
    os2.fsSelection = (os2.fsSelection | 1) & ~(1 << 6)      # ITALIC on, REGULAR off
    f["head"].macStyle = (f["head"].macStyle | 2)

    n = f["name"]
    fam_full = n.getDebugName(16) or n.getDebugName(1)       # "Ferrum Mono"
    ps_fam = n.getDebugName(6).split("-")[0]                # "FerrumMono"
    weight = os.path.basename(src)[:-4].split("-")[-1]       # "Thin", "Regular" ...
    ribbi = weight in ("Regular", "Bold")
    style = "Italic" if weight == "Regular" else f"{weight} Italic"
    ps_style = "Italic" if weight == "Regular" else f"{weight}Italic"
    rev = n.getDebugName(3).split(";")[-1]
    pid, eid, lid = 3, 1, 0x409
    n.setName(fam_full if ribbi else f"{fam_full} {weight}", 1, pid, eid, lid)
    n.setName(("Bold Italic" if weight == "Bold" else "Italic"), 2, pid, eid, lid)
    n.setName(f"{ps_fam}-{ps_style};{rev}", 3, pid, eid, lid)
    n.setName(f"{fam_full} {style}", 4, pid, eid, lid)
    n.setName(f"{ps_fam}-{ps_style}", 6, pid, eid, lid)
    if ribbi:
        n.removeNames(nameID=16); n.removeNames(nameID=17)
    else:
        n.setName(fam_full, 16, pid, eid, lid)
        n.setName(style, 17, pid, eid, lid)
    f.save(dst)

    subprocess.run([sys.executable, "-m", "ttfautohint", "--composites", "--windows-compatibility",
                    "--default-script=latn", "--fallback-script=latn", dst, dst + ".tmp"], check=True)
    os.replace(dst + ".tmp", dst)


WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular",
                500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def add_stat(path):
    """Static-font STAT: one value per axis, this font's own location."""
    f = TTFont(path)
    n = f["name"]
    if "STAT" in f:                                  # re-run: drop the old table and its names
        st = f["STAT"].table
        old = {a.AxisNameID for a in st.DesignAxisRecord.Axis}
        old |= {v.ValueNameID for v in (st.AxisValueArray.AxisValue if st.AxisValueArray else [])}
        n.names = [r for r in n.names if r.nameID not in old or r.nameID < 256]
        del f["STAT"]
    n.names = [r for r in n.names if r.platformID != 1]
    wght = f["OS/2"].usWeightClass
    italic = bool(f["OS/2"].fsSelection & 1)
    w = dict(value=wght, name=WEIGHT_NAMES.get(wght, str(wght)))
    if wght == 400:
        w.update(flags=0x2, linkedValue=700)
    i = dict(value=1, name="Italic") if italic else dict(value=0, name="Roman", flags=0x2, linkedValue=1)
    axes = [dict(tag="wght", name="Weight", values=[w]), dict(tag="ital", name="Italic", values=[i])]
    buildStatTable(f, axes, locations=None, elidedFallbackName=2, macNames=False)
    f.save(path)

for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.ttf"))):
    base = os.path.basename(p)[:-4]
    if base.endswith("Italic"):
        continue
    fam, weight = base.rsplit("-", 1)
    out = os.path.join(sys.argv[1], f"{fam}-{'Italic' if weight == 'Regular' else weight + 'Italic'}.ttf")
    build(p, out)
    print(os.path.basename(out))

for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.ttf"))):
    add_stat(p)
