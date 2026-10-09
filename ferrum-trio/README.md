# Ferrum Trio

The letters of [Ferrum Mono](../ferrum-mono/) on a grid of three widths, for
running text, headings and UI: half a cell for the narrow letters, one cell
for most, one and a half for the wide ones. Latin and Cyrillic, eight weights
from Thin to ExtraBold with italics, kerning on by default.

![Ferrum Trio specimen](specimen.png)

| Width | Glyphs |
|---|---|
| ½ cell | space, I i l and their accented forms, І і Ї ї, `. , : ; ! \| ' ’` |
| 1 cell | everything else; digits stay tabular |
| 1½ cell | М Ш Щ Ю Ж Ы Љ Њ Җ, M W Æ Œ, their lowercase and accented forms |

Narrow letters keep their slab serifs, trimmed to the half cell. Wide letters
get the extra width in their counters, not their strokes, and the three-stem
letters (m ш щ ы, M Ш Щ Ы) get back the full stem weight the mono cell took
from them.

For code and terminals use Ferrum Mono; Trio is not monospaced.

## Use on the web

```html
<link rel="stylesheet" href="/fonts/webfonts/ferrum-trio.css">
```

```css
body, h1, h2 { font-family: "Ferrum Trio", system-ui, sans-serif; }
code, pre    { font-family: "Ferrum Mono", ui-monospace, monospace; }
```

Each weight is a ~56 KB WOFF2 file. Load only the weights you use.

To let the browser download only the scripts a page uses, link the split
stylesheet instead: `fonts/webfonts/subset/ferrum-trio-subset.css` (latin,
latin-ext, cyrillic, cyrillic-ext and symbols per weight; a Russian page loads
about 41 KB per weight instead of 56). Kerning between a Latin and a Cyrillic
letter sitting side by side is not applied with the split files, since the
browser shapes each file separately.

### Variable font

`fonts/variable/` has every weight in one file, upright and italic:
`FerrumTrio[wght]` (~186 KB WOFF2) and `FerrumTrio-Italic[wght]` (~201 KB), wght
100–800, any weight in between:

```html
<link rel="stylesheet" href="/fonts/variable/ferrum-trio-variable.css">
```

```css
p  { font-family: "Ferrum Trio"; font-weight: 450; }
em { font-style: italic; }
```

The variable fonts are unhinted; for small text on Windows the hinted static
fonts render crisper.

## Install on your computer

Install the files from `fonts/ttf/`.

## Italics

Every weight has an italic: a 10° oblique of the upright (Geist Mono Italic
leans 12°, JetBrains Mono about 9°; 10° keeps tall letters inside the cell).
Strokes are corrected after the slant so they keep their upright thickness,
whatever their direction. Files: `FerrumTrio-Italic`, `FerrumTrio-BoldItalic`,
`FerrumTrio-ThinItalic` …; the stylesheet maps them to `font-style: italic`.

## Features

| Feature | What it does |
|---|---|
| `kern` | Pair kerning (Ferrum Mono's ss20), on by default |
| `ss01` | Coding ligatures |
| `ss04` | Small arrows |
| `cv01` | Single-story a |
| `cv02` | Ж ж Җ җ with the step spread wider |
| `zero` | Slashed zero |
| `smcp`, `c2sc` | Small caps from lowercase / from capitals (Latin and Cyrillic) |
| `pnum` | Proportional 1 on the half cell (other figures stay one cell) |
| `locl` | Bulgarian, Serbian and Macedonian letterforms (from Ferrum Mono) |

## Building

Ferrum Trio is built from the finished Ferrum Mono fonts:

```sh
cd scripts
python3 trio.py     ../../ferrum-mono/fonts/ttf ../fonts/ttf
python3 hint.py     ../fonts/ttf
python3 oblique.py  ../fonts/ttf
python3 webfonts.py ../fonts/ttf ../fonts/webfonts
python3 specimen.py ../fonts/ttf ../specimen.png ../../ferrum-mono/fonts/ttf
python3 subset.py   ../fonts/ttf ../fonts/webfonts/subset

python3 variable.py PAPER_VAR GEIST_VAR work ../fonts/variable   # Mono's variable masters -> trio.py --variable -> varLib (+ italic)
```

## License

SIL Open Font License 1.1, see [OFL.txt](../OFL.txt). Changes are listed in
[FONTLOG.md](FONTLOG.md).
