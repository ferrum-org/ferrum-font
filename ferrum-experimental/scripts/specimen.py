"""Render specimen.png for Ferrum Experimental (HarfBuzz shaping, Skia drawing).

    pip install skia-python uharfbuzz
    python3 specimen.py ../fonts/ttf ../specimen.png

Uses ../fonts/nerd (Ferrum Experimental NF) next to the ttf folder for the terminal row.
"""
import sys, os
import skia, uharfbuzz as hb

TTF, OUT = sys.argv[1], sys.argv[2]
NERD = os.path.join(os.path.dirname(os.path.abspath(TTF)), "nerd")
WEIGHTS = ["Thin", "ExtraLight", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold"]
BG, FG, DIM, ACC, GRID = 0xFF0E0E10, 0xFFEDEBE6, 0xFF7A7A80, 0xFFC9551F, 0xFF26262B
GREEN, RED, BLUE, PILL = 0xFF93B373, 0xFFD4654D, 0xFF7AA2C8, 0xFF26262B
W, M = 2000, 70
_fonts = {}


def path(style, nerd=False):
    return os.path.join(NERD, f"FerrumExperimentalNF-{style}.ttf") if nerd else os.path.join(TTF, f"FerrumExperimental-{style}.ttf")


def italic(w):
    return "Italic" if w == "Regular" else w + "Italic"


def font(p):
    if p not in _fonts:
        face = hb.Face(hb.Blob.from_file_path(p))
        _fonts[p] = (hb.Font(face), face.upem, skia.Typeface.MakeFromFile(p))
    return _fonts[p]


def text(c, style, size, x, y, s, color=FG, features=None, lang=None, nerd=False):
    hf, upem, tf = font(path(style, nerd))
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    if lang:
        buf.language = lang
    hb.shape(hf, buf, features or {})
    f = skia.Font(tf, size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setHinting(skia.FontHinting.kNone); f.setSubpixel(True)
    k, cx, glyphs, pts = size / upem, 0, [], []
    for i, p in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append(i.codepoint); pts.append(skia.Point(x + (cx + p.x_offset) * k, y - p.y_offset * k)); cx += p.x_advance
    b = skia.TextBlobBuilder(); b.allocRunPos(f, glyphs, pts)
    c.drawTextBlob(b.make(), 0, 0, skia.Paint(AntiAlias=True, Color=color))
    return cx * k


def rule(c, y):
    c.drawLine(M, y, W - M, y, skia.Paint(Color=GRID, StrokeWidth=1.5))


def label(c, y, s):
    text(c, "Regular", 22, M, y, s, ACC)


surf = skia.Surface(W, 3600)
c = surf.getCanvas()
c.clear(BG)

# --- title --------------------------------------------------------------------
text(c, "SemiBold", 124, M, 150, "Ferrum Experimental")
text(c, "Regular", 30, M, 208, "arch + contrast build · Latin + Cyrillic · 8 weights + italics · NF · OFL 1.1", DIM)

# --- weights, upright and italic -----------------------------------------------
y = 320
for w in WEIGHTS:
    text(c, "Regular", 22, M, y - 6, w, DIM)
    x = text(c, w, 46, 300, y, "Железный ферзь — Iron queen 0123")
    text(c, italic(w), 46, 300 + x + 60, y, "Курсив · Italic", FG)
    y += 70

# --- alphabets -------------------------------------------------------------------
y += 40; rule(c, y); y += 70
for line in ("ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz",
             "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ ҐЄІЇЎ",
             "абвгдеёжзийклмнопрстуфхцчшщъыьэюя ґєіїў",
             "0123456789 {}[]()<>=+-*/&|!?@#$%^~ «» — № ✓ ✗"):
    text(c, "Regular", 38, M, y, line)
    y += 62

# --- code -------------------------------------------------------------------------
y += 20; rule(c, y); y += 70
code = [
    [("use ", BLUE), ("ferrum::net::Socket;", FG)],
    [("// Соединение с узлом: повтор при ошибке", DIM, "Italic")],
    [("async fn ", BLUE), ("connect", ACC), ("(addr: &str) -> Result<Socket> {", FG)],
    [("    let ", BLUE), ("sock = Socket::bind(", FG), ("\"0.0.0.0:7700\"", GREEN), (").await?;", FG)],
    [("    sock.dial(addr).await ", FG), ("// → ok", DIM, "Italic")],
    [("}", FG)],
]
for line in code:
    x = M
    for part in line:
        s, col = part[0], part[1]
        st = part[2] if len(part) > 2 else "Regular"
        x += text(c, st, 36, x, y, s, col)
    y += 52

# --- terminal (Ferrum Mono NF) -----------------------------------------------------
y += 40; rule(c, y); y += 60
label(c, y, "Ferrum Experimental NF · terminal"); y += 70
segs = [(0xFF2F5FA8, "  ferrum "), (ACC, "  ~/ferrum-font "), (0xFF3D8B4A, "  main  ")]
size = 40; cw = 606 * size / 1000
x = M
for i, (col, s) in enumerate(segs):
    wpx = len(s) * cw
    c.drawRect(skia.Rect(x, y - size * 0.86, x + wpx, y + size * 0.3), skia.Paint(Color=col))
    text(c, "Bold", size, x, y, s, 0xFFFFFFFF, nerd=True)
    x += wpx
    nxt = segs[i + 1][0] if i + 1 < len(segs) else BG
    c.drawRect(skia.Rect(x, y - size * 0.86, x + cw, y + size * 0.3), skia.Paint(Color=nxt))
    text(c, "Regular", size, x, y, "", col, nerd=True)
    x += cw
y += 66
x = text(c, "Regular", 36, M, y, " cargo test  ", FG, nerd=True)
x += text(c, "Regular", 36, M + x, y, "✓ 41 passed  ", GREEN, nerd=True)
x += text(c, "Regular", 36, M + x, y, "✗ 1 failed  ", RED, nerd=True)
text(c, "Regular", 36, M + x, y, " 0.8s", DIM, nerd=True)
y += 56
text(c, "Regular", 36, M, y, " src    main.rs    Cargo.toml    README.md    .gitignore", FG, nerd=True)

# --- features ----------------------------------------------------------------------
y += 50; rule(c, y); y += 60
label(c, y, "ss20 · кернинг для текста (выключен по умолчанию)"); y += 66
sample = "ГЛАВНЫЙ ТРАКТ — Тула, «Тайга»."
text(c, "Regular", 50, M, y, sample, DIM)
y += 66
text(c, "Regular", 50, M, y, sample, FG, {"ss20": True})
y += 80
label(c, y, "locl · ru / bg / sr"); y += 62
text(c, "Regular", 44, M, y, "вгджзийклптцшщю", FG, lang="ru")
text(c, "Regular", 44, M + 700, y, "вгджзийклптцшщю", FG, lang="bg")
text(c, "Regular", 44, M + 1400, y, "бабо · Србија", FG, lang="sr")
y += 80
label(c, y, "cv02 · Ж с разведённой ступенькой"); y += 72
x = text(c, "ExtraBold", 64, M, y, "Жж ", FG)
text(c, "ExtraBold", 64, M + x, y, "Жж", ACC, {"cv02": True})
y += 70

surf.makeImageSnapshot().makeSubset(skia.IRect(0, 0, W, y)).save(OUT, skia.kPNG)
print(OUT, W, y)
