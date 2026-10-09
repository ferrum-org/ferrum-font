"""Render specimen.png for Ferrum Trio (HarfBuzz shaping, Skia drawing).

    pip install skia-python uharfbuzz
    python3 specimen.py ../fonts/ttf ../specimen.png [../../ferrum-mono/fonts/ttf]

With the Ferrum Mono folder given, the same paragraph is shown in both.
"""
import sys, os
import skia, uharfbuzz as hb

TTF, OUT = sys.argv[1], sys.argv[2]
MONO = sys.argv[3] if len(sys.argv) > 3 else None
WEIGHTS = ["Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold"]
BG, FG, DIM, GRID, ACC = 0xFF0E0E10, 0xFFEDEBE6, 0xFF7A7A80, 0xFF2A2A30, 0xFFC9551F
W, M = 2000, 70
_fonts = {}


def font(path):
    if path not in _fonts:
        face = hb.Face(hb.Blob.from_file_path(path))
        _fonts[path] = (hb.Font(face), face.upem, skia.Typeface.MakeFromFile(path))
    return _fonts[path]


def trio(w): return os.path.join(TTF, f"FerrumTrio-{w}.ttf")
def mono(w): return os.path.join(MONO, f"FerrumMono-{w}.ttf")


def text(c, path, size, x, y, s, color=FG, cells=False, features=None, lang=None):
    hf, upem, tf = font(path)
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    if lang:
        buf.language = lang
    hb.shape(hf, buf, features or {})
    f = skia.Font(tf, size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setHinting(skia.FontHinting.kNone); f.setSubpixel(True)
    k, cx, glyphs, pts = size / upem, 0, [], []
    grid = skia.Paint(Color=GRID, StrokeWidth=1.5)
    for i, p in zip(buf.glyph_infos, buf.glyph_positions):
        if cells:
            c.drawLine(x + cx * k, y - size * 0.85, x + cx * k, y + size * 0.25, grid)
        glyphs.append(i.codepoint); pts.append(skia.Point(x + (cx + p.x_offset) * k, y - p.y_offset * k)); cx += p.x_advance
    if cells:
        c.drawLine(x + cx * k, y - size * 0.85, x + cx * k, y + size * 0.25, grid)
    b = skia.TextBlobBuilder(); b.allocRunPos(f, glyphs, pts)
    c.drawTextBlob(b.make(), 0, 0, skia.Paint(AntiAlias=True, Color=color))
    return cx * k


surf = skia.Surface(W, 2600)
c = surf.getCanvas()
c.clear(BG)

text(c, trio("SemiBold"), 124, M, 150, "Ferrum Trio")
text(c, trio("Regular"), 30, M, 208, "Three widths · ½ · 1 · 1½ cell · Latin + Cyrillic · 8 weights + italics · variable · OFL 1.1", DIM)

y = 380
text(c, trio("Regular"), 22, M, y - 110, "сетка: полторы ячейки, ячейка, пол-ячейки", ACC)
text(c, trio("Regular"), 88, M, y, "Шил, Жюль, Mill.", cells=True)
y += 150

for w in WEIGHTS:
    text(c, trio("Regular"), 22, M, y - 6, w, DIM)
    x = text(c, trio(w), 52, 330, y, "Железный ферзь — Iron queen 0123")
    text(c, trio("Italic" if w == "Regular" else w + "Italic"), 52, 330 + x + 50, y, "Курсив")
    y += 78

y += 60
para = ["Широкая электрификация южных губерний даст мощный",
        "толчок подъёму сельского хозяйства. Will we mimic it?"]
if MONO:
    text(c, trio("Regular"), 22, M, y, "Ferrum Mono", DIM); y += 56
    for line in para:
        text(c, mono("Regular"), 38, M, y, line, DIM); y += 56
    y += 30
    text(c, trio("Regular"), 22, M, y, "Ferrum Trio", ACC); y += 56
for line in para:
    text(c, trio("Regular"), 38, M, y, line); y += 56

y += 70
text(c, trio("Regular"), 22, M, y, "smcp · c2sc · pnum · locl bg", ACC); y += 70
text(c, trio("Regular"), 48, M, y, "Москва · Жюль Верн · NASA", FG, features={"smcp": True}); y += 68
text(c, trio("Regular"), 48, M, y, "с 1991 по 2011 год · 11:41", FG, features={"pnum": True}); y += 68
text(c, trio("Regular"), 48, M, y, "Съединението прави силата", FG, lang="bg"); y += 20

y += 60
for line in ("ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz",
             "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ ҐЄІЇЎ",
             "абвгдеёжзийклмнопрстуфхцчшщъыьэюя ґєіїў",
             "0123456789 {}[]()<>=+-*/&|!?@#$%^~ «» — №"):
    text(c, trio("Regular"), 38, M, y, line)
    y += 64
y += 30

surf.makeImageSnapshot().makeSubset(skia.IRect(0, 0, W, y)).save(OUT, skia.kPNG)
print(OUT, W, y)
