"""Web subsets: one WOFF2 per script range, with a unicode-range @font-face
for each, so a browser downloads only the ranges a page uses.

    python3 subset.py ../fonts/ttf ../fonts/webfonts/subset

All OpenType features are kept within each subset. A kerning pair whose two
letters fall in different subsets (a Latin letter next to a Cyrillic one) is
not applied, since the browser shapes each font file separately; the full
WOFF2 files next to this folder keep everything in one file.
"""
import sys, os, glob, re
from fontTools.ttLib import TTFont
from fontTools import subset

SRC, DST = sys.argv[1], sys.argv[2]
WEIGHTS = {"Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400,
           "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800}
MARKS = "U+0300-036F"     # combining marks go with both Latin and Cyrillic, so they attach
RANGES = [                # Google Fonts' ranges, plus the combining marks
    ("cyrillic-ext", "U+0460-052F, U+1C80-1C88, U+20B4, U+2DE0-2DFF, U+A640-A69F, U+FE2E-FE2F, " + MARKS),
    ("cyrillic", "U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116, " + MARKS),
    ("latin-ext", "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+1D00-1DBF, "
                  "U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, "
                  "U+A720-A7FF, " + MARKS),
    ("latin", "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+2000-206F, "
              "U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD, " + MARKS),
]


def parse(r):
    out = set()
    for part in r.split(","):
        a, _, b = part.strip()[2:].partition("-")
        out.update(range(int(a, 16), int(b or a, 16) + 1))
    return out


def ranges(cps):
    """Compact unicode-range string for a set of codepoints."""
    cps = sorted(cps); out = []; i = 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append(f"U+{cps[i]:04X}" if i == j else f"U+{cps[i]:04X}-{cps[j]:04X}")
        i = j + 1
    return ", ".join(out)


os.makedirs(DST, exist_ok=True)
css, report = [], []
family = None
for p in sorted(glob.glob(os.path.join(SRC, "*.ttf"))):
    stem = os.path.basename(p)[:-4]
    prefix, weight = stem.rsplit("-", 1)
    italic = weight.endswith("Italic")
    if italic:
        weight = weight[:-len("Italic")] or "Regular"           # BoldItalic -> Bold, Italic -> Regular
    family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", prefix)          # FerrumMono -> Ferrum Mono
    cmap = set(TTFont(p).getBestCmap())
    covered = set()
    sets = []
    for name, r in RANGES:
        cps = parse(r) & cmap
        covered |= cps
        sets.append((name, cps, r))
    rest = cmap - covered
    sets.append(("symbols", rest, ranges(rest)))
    for name, cps, r in sets:
        if not cps:
            continue
        o = subset.Options()
        o.layout_features = ["*"]; o.name_IDs = ["*"]; o.name_languages = ["*"]
        o.hinting = True; o.notdef_outline = True; o.glyph_names = False
        o.drop_tables = o.drop_tables + ["meta"]
        f = TTFont(p)
        s = subset.Subsetter(o); s.populate(unicodes=cps); s.subset(f)
        f.flavor = "woff2"
        fn = f"{stem}.{name}.woff2"
        f.save(os.path.join(DST, fn))
        size = os.path.getsize(os.path.join(DST, fn))
        if weight == "Regular" and not italic:
            report.append(f"{name:13s} {size / 1024:6.1f} KB")
        style = "italic" if italic else "normal"
        css.append(f"/* {name} */\n@font-face {{ font-family: \"{family}\"; font-style: {style}; "
                   f"font-weight: {WEIGHTS[weight]}; font-display: swap; src: url(\"{fn}\") format(\"woff2\"); "
                   f"unicode-range: {r}; }}")

slug = family.lower().replace(" ", "-")
head = (f"/*\n * {family}, split by script: the browser downloads only the ranges a page uses.\n"
        f" * SIL Open Font License 1.1 (see OFL.txt in the repository root).\n"
        f" * Kerning between letters of different subsets (Latin next to Cyrillic) is not applied;\n"
        f" * use ../{slug}.css (one file per weight) where that matters.\n */\n")
open(os.path.join(DST, f"{slug}-subset.css"), "w", encoding="utf-8", newline="\n").write(head + "\n".join(css) + "\n")
print(f"{family}: {len(css)} faces", *report, sep="\n")
