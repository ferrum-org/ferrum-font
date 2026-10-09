# Ferrum Mono

The monospace typeface of the ferrum project: Latin and Cyrillic, eight weights
from Thin to ExtraBold with italics, with optional text kerning.

![Ferrum Mono specimen](specimen.png)

## Use on the web

Copy `fonts/webfonts/` into your site and include the stylesheet:

```html
<link rel="stylesheet" href="/fonts/webfonts/ferrum-mono.css">
```

```css
code, pre { font-family: "Ferrum Mono", ui-monospace, monospace; }

/* Headings and running text: turn on kerning */
h1, h2, .lead { font-family: "Ferrum Mono", monospace; font-feature-settings: "ss20"; }
```

Each weight is a ~57 KB WOFF2 file. Load only the weights you use.

To let the browser download only the scripts a page uses, link the split
stylesheet instead: `fonts/webfonts/subset/ferrum-mono-subset.css` (latin,
latin-ext, cyrillic, cyrillic-ext and symbols per weight; a Russian page loads
about 41 KB per weight instead of 57). Kerning between a Latin and a Cyrillic
letter sitting side by side is not applied with the split files, since the
browser shapes each file separately.

### Variable font

`fonts/variable/` has every weight in one file, upright and italic:
`FerrumMono[wght]` (~146 KB WOFF2) and `FerrumMono-Italic[wght]` (~160 KB), wght
100–800, any weight in between:

```html
<link rel="stylesheet" href="/fonts/variable/ferrum-mono-variable.css">
```

```css
p  { font-family: "Ferrum Mono"; font-weight: 450; }
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
whatever their direction. Box drawing and block elements stay upright so they
still tile. Files: `FerrumMono-Italic`, `FerrumMono-BoldItalic`,
`FerrumMono-ThinItalic` …; the stylesheet maps them to `font-style: italic`.

## Terminals: Ferrum Mono NF

`fonts/nerd/` holds **Ferrum Mono NF**: the same fonts with the
[Nerd Fonts](https://www.nerdfonts.com) icons added (Powerline, Devicons,
Font Awesome, Material Design, Codicons, Octicons and the rest, ~10,600
symbols), each one cell wide, for prompts such as Starship or oh-my-posh and
for file-tree icons. Install them and pick the face `Ferrum Mono NF`, e.g. in
Windows Terminal:

```json
"font": { "face": "Ferrum Mono NF" }
```

The icons keep their own licenses, listed in
[fonts/nerd/LICENSES.md](fonts/nerd/LICENSES.md).

## Features

| Feature | What it does |
|---|---|
| `ss20` | Pair kerning for text (~8,000 pairs per weight). Off by default, so code and terminals keep the monospace grid. See [kerning.png](kerning.png). |
| `ss01` | Coding ligatures |
| `ss02` | Duospace glyphs (M W m w … 1.25 cells wide; breaks the grid, keep it out of code) |
| `ss03` | Narrow space |
| `ss04` | Small arrows |
| `cv01` | Single-story a |
| `cv02` | Ж ж Җ җ with the step spread wider |
| `zero` | Slashed zero |
| `locl` | Bulgarian (`lang="bg"`), Serbian (`sr`) and Macedonian (`mk`) letterforms, applied automatically by the text's language |

## Origins

Ferrum Mono is a modified version of
[Paper Mono](https://github.com/paper-design/paper-mono) by Paper, which is
itself based on [Geist Mono](https://github.com/vercel/geist-font) by Vercel.
Paper Mono has no Cyrillic; Ferrum Mono adds it from Geist Mono, fitted to
Paper Mono's metrics, with several letters rebuilt and the whole set re-spaced
and kerned. See [FONTLOG.md](FONTLOG.md) for the full list of changes.

Ferrum Mono is not affiliated with or endorsed by Paper (Lost Coast Labs, Inc.)
or Vercel.

## Building

The build scripts are in [`scripts/`](scripts/README.md).

## License

SIL Open Font License 1.1 — see [OFL.txt](../OFL.txt). You can use, modify and
redistribute the fonts, including in commercial products; the fonts themselves
may not be sold on their own, and modified versions must stay under the OFL.
