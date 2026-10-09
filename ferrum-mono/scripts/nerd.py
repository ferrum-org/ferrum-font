"""Ferrum Mono NF: Ferrum Mono with the Nerd Fonts symbols, for terminals.

    python3 nerd.py ../fonts/ttf ../fonts/nerd [SymbolsNerdFontMono-Regular.ttf]

Without the third argument the symbols font is downloaded from the latest
nerd-fonts release (NerdFontsSymbolsOnly.zip).

- Every icon is one cell (606) wide, scaled with its aspect kept to the cell
  width and centred on the line, like the Nerd Fonts "Mono" variant.
- Powerline separators (U+E0B0-E0D7) are stretched to the whole cell and line
  (the same overshoot as the box-drawing glyphs), so prompt segments join.
- Existing Ferrum Mono glyphs are never replaced.
- The Latin and Cyrillic keep Ferrum Mono's hinting byte for byte; the icons
  are added without instructions (ttfautohint would distort pictograms).
"""
import sys, os, io, zipfile, json, urllib.request
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SRC, DST = sys.argv[1], sys.argv[2]
SYM = sys.argv[3] if len(sys.argv) > 3 else None
CELL = 606
POWERLINE = range(0xE0B0, 0xE0D8)      # separators: stretched to the cell
BOX_Y = (-265, 975)                    # same overshoot as Ferrum Mono's box drawing
BOX_X = (-5, CELL + 5)


def symbols_font():
    if SYM:
        return TTFont(SYM)
    api = "https://api.github.com/repos/ryanoasis/nerd-fonts/releases/latest"
    tag = json.load(urllib.request.urlopen(api))["tag_name"]
    url = f"https://github.com/ryanoasis/nerd-fonts/releases/download/{tag}/NerdFontsSymbolsOnly.zip"
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read()))
    return TTFont(io.BytesIO(z.read("SymbolsNerdFontMono-Regular.ttf")))


def merge(path, sym, out):
    f = TTFont(path)
    cmap = f.getBestCmap()
    scmap = sym.getBestCmap()
    sglyf, sgs = sym["glyf"], sym.getGlyphSet()
    s_upm = sym["head"].unitsPerEm
    s_asc, s_dsc = sym["hhea"].ascent, sym["hhea"].descent
    asc, dsc = f["hhea"].ascent, f["hhea"].descent
    k = CELL / s_upm                                  # icon box (s_upm square) -> one cell
    line_mid = (asc + dsc) / 2
    s_mid = (s_asc + s_dsc) / 2

    glyf, hmtx = f["glyf"], f["hmtx"]
    order = list(f.getGlyphOrder())
    names = set(order)
    mapping = dict(cmap)
    added = 0
    for u, sname in sorted(scmap.items()):
        if u in cmap:
            continue                                  # never replace our own glyphs
        g = sglyf[sname]
        g.recalcBounds(sglyf)
        # production names (uniE0B0, u0F001): the Nerd Fonts names (cod-add, ...)
        # use hyphens, which are not valid glyph names
        name = f"uni{u:04X}" if u <= 0xFFFF else f"u{u:05X}"
        if name in names:
            continue
        pen = TTGlyphPen(None)
        if u in POWERLINE and g.numberOfContours:
            x0, y0, x1, y1 = g.xMin, g.yMin, g.xMax, g.yMax
            sx = (BOX_X[1] - BOX_X[0]) / max(1, x1 - x0)
            sy = (BOX_Y[1] - BOX_Y[0]) / max(1, y1 - y0)
            m = (sx, 0, 0, sy, BOX_X[0] - x0 * sx, BOX_Y[0] - y0 * sy)
        else:
            m = (k, 0, 0, k, 0, line_mid - s_mid * k)
        sgs[sname].draw(TransformPen(pen, m))
        ng = pen.glyph()
        ng.recalcBounds(glyf)
        glyf[name] = ng
        hmtx[name] = (CELL, getattr(ng, "xMin", 0))
        order.append(name); names.add(name)
        mapping[u] = name
        added += 1
    f.setGlyphOrder(order)
    glyf.glyphOrder = order

    # cmap: BMP in format 4, everything (Material Design is in plane 15) in format 12
    tables = []
    for pid, eid, fmt in ((0, 3, 4), (3, 1, 4), (0, 4, 12), (3, 10, 12)):
        t = CmapSubtable.newSubtable(fmt)
        t.platformID, t.platEncID, t.language = pid, eid, 0
        t.cmap = {u: n for u, n in mapping.items() if fmt == 12 or u <= 0xFFFF}
        tables.append(t)
    f["cmap"].tables = tables

    for t in ("hdmx", "LTSH", "VDMX"):
        if t in f:
            del f[t]
    os2 = f["OS/2"]
    os2.ulUnicodeRange2 |= 1 << (57 - 32)             # non-plane 0
    os2.ulUnicodeRange2 |= 1 << (60 - 32)             # private use area
    os2.usLastCharIndex = min(0xFFFF, max(mapping))
    os2.recalcAvgCharWidth(f)
    f["post"].isFixedPitch = 1
    os2.panose.bProportion = 9

    for r in f["name"].names:
        s = r.toUnicode()
        s = s.replace("Ferrum Mono", "Ferrum Mono NF").replace("FerrumMono", "FerrumMonoNF")
        if r.nameID == 10:
            s += (" Nerd Fonts symbols (https://www.nerdfonts.com) added for terminals;"
                  " see LICENSES.md for the icon sets.")
        r.string = s
    f.save(out)
    return added


os.makedirs(DST, exist_ok=True)
sym = symbols_font()
for p in sorted(os.listdir(SRC)):
    if p.startswith("FerrumMono-") and p.endswith(".ttf") and not p.endswith("Italic.ttf"):   # uprights only
        out = os.path.join(DST, p.replace("FerrumMono-", "FerrumMonoNF-"))
        n = merge(os.path.join(SRC, p), sym, out)
        print(os.path.basename(out), f"+{n} symbols", os.path.getsize(out) // 1024, "KB")
