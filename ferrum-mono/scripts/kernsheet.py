"""Render kerning.png: what ss20 does (off by default, on for text).

    python3 kernsheet.py ../fonts/ttf pairs.json ../kerning.png
"""
import sys, os, json
import skia, uharfbuzz as hb

TTF, PAIRS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
BG, FG, DIM, FAINT, GRID, ACC = 0xFF0E0E10, 0xFFEDEBE6, 0xFF7A7A80, 0xFF4A4A50, 0xFF26262B, 0xFFC9551F
W, M = 2000, 70
pairs = json.load(open(PAIRS, encoding="utf-8"))
_fonts = {}


def font(weight):
    if weight not in _fonts:
        p = os.path.join(TTF, f"FerrumMono-{weight}.ttf")
        face = hb.Face(hb.Blob.from_file_path(p))
        _fonts[weight] = (hb.Font(face), face.upem, skia.Typeface.MakeFromFile(p))
    return _fonts[weight]


def text(c, weight, size, x, y, s, color=FG, kern=False):
    hf, upem, tf = font(weight)
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    hb.shape(hf, buf, {"ss20": True} if kern else {})
    f = skia.Font(tf, size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setHinting(skia.FontHinting.kNone); f.setSubpixel(True)
    k, cx, glyphs, pts = size / upem, 0, [], []
    for i, p in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append(i.codepoint); pts.append(skia.Point(x + (cx + p.x_offset) * k, y - p.y_offset * k)); cx += p.x_advance
    b = skia.TextBlobBuilder(); b.allocRunPos(f, glyphs, pts)
    c.drawTextBlob(b.make(), 0, 0, skia.Paint(AntiAlias=True, Color=color))
    return cx * k


def cells(c, size, x, y, n):
    """The monospace grid behind a line: one cell = 606 units."""
    w = 606 * size / 1000
    p = skia.Paint(Color=GRID, StrokeWidth=1.5)
    for i in range(n + 1):
        c.drawLine(x + i * w, y - size * 0.82, x + i * w, y + size * 0.22, p)


surf = skia.Surface(W, 2600)
c = surf.getCanvas()
c.clear(BG)

text(c, "SemiBold", 64, M, 120, "ss20 · кернинг для текста")
text(c, "Regular", 26, M, 172, "Моноширинный по умолчанию: каждая буква в ячейке, код и терминалы держат сетку.", DIM)
text(c, "Regular", 26, M, 210, "Для заголовков и текста ss20 включает парный кернинг — около 8 000 пар на начертание.", DIM)

y = 360
for line in ("ГЛАВНЫЙ ТРАКТ — Тула, «Тайга».", "AVATAR · Type · Tokyo · Yoga"):
    text(c, "Regular", 20, M, y - 70, "по умолчанию (off)", DIM)
    cells(c, 66, M, y, len(line))
    text(c, "Medium", 66, M, y, line, FAINT)
    y += 120
    text(c, "Regular", 20, M, y - 70, "ss20 on", ACC)
    text(c, "Medium", 66, M, y, line, FG, kern=True)
    y += 140

# pair table ------------------------------------------------------------
y += 10
text(c, "Regular", 26, M, y, "Пары (Regular, единицы на 1000 em)", DIM)
y += 40
want = ["ТА", "Та", "То", "Ту", "Тя", "ГА", "Го", "Гд", "ГЛ", "УА", "Уд", "Ул",
        "РА", "Ра", "ЬТ", "ЪТ", "ДТ", "Г.", "Т,", "«Т", "LT", "AV", "AT", "VA",
        "LY", "Yo", "Fa", "Wa", "Vo", "P."]
reg = pairs["Regular"]
table = [(p, reg[p]) for p in want if p in reg][:30]
cols, cw, ch = 6, (W - 2 * M) // 6, 210
for i, (p, v) in enumerate(table):
    x = M + (i % cols) * cw
    yy = y + (i // cols) * ch
    c.drawRoundRect(skia.Rect(x, yy, x + cw - 18, yy + ch - 18), 14, 14, skia.Paint(Color=0xFF16161A, AntiAlias=True))
    text(c, "Regular", 64, x + 22, yy + 82, p, FAINT)
    text(c, "Regular", 64, x + 22, yy + 160, p, FG, kern=True)
    text(c, "Regular", 24, x + cw - 100, yy + 44, f"{v:+d}", ACC)
y += ((len(table) + cols - 1) // cols) * ch + 60

# how ----------------------------------------------------------------------
text(c, "Regular", 26, M, y, "Как включить", DIM)
y += 56
for line, col in (('h1, h2, .lead {', FG),
                  ('  font-family: "Ferrum Mono", monospace;', FG),
                  ('  font-feature-settings: "ss20";   /* только для текста */', FG),
                  ('}', FG),
                  ('code, pre, terminal — без ss20: сетка важнее', DIM)):
    text(c, "Regular", 32, M, y, line, col)
    y += 48
y += 40
n = {w: len(v) for w, v in pairs.items()}
text(c, "Regular", 20, M, y, "Пар на начертание: " + " · ".join(f"{w} {n[w]}" for w in
     ("Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold") if w in n), DIM)
y += 60

surf.makeImageSnapshot().makeSubset(skia.IRect(0, 0, W, y)).save(OUT, skia.kPNG)
print(OUT, W, y)
