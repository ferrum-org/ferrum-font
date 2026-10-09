# FONTLOG — Ferrum Trio

Ferrum Trio is the quasi-proportional companion of Ferrum Mono: the same
letters on three widths (½, 1 and 1½ of Ferrum Mono's 606-unit cell). It is
built from Ferrum Mono, a modified version of Paper Mono with Cyrillic adapted
from Geist Mono, and is released under the SIL Open Font License 1.1.

Ferrum Trio is not affiliated with or endorsed by Paper (Lost Coast Labs, Inc.)
or Vercel.

## 1.004

Built from Ferrum Mono 1.005: diagonal tops on l and r (`arch.py`),
stronger pen contrast (VERT 0.024, HORZ 0.090), wider bottom arches
(CALM 0.26 — о е р б ц no longer pinch in ExtraBold).

## 1.003

Built from Ferrum Mono 1.004: open terminals (cut across the stroke, +20°)
and humanist contrast with a 30° axis.

## 1.002

Built from Ferrum Mono 1.003.

- Bulgarian / Serbian / Macedonian forms from Ferrum Mono, on the grid by
  shape: ɯ-shaped ш щ wide like ш, т (m) wide, п (n) and the rest one cell;
  ж and ю keep their ascender stem in the wide cell.
- Small caps (smcp, c2sc) for every Latin and Cyrillic capital with a
  lowercase pair: height 540 (x-height + 6%), 15% wider than a straight
  scale, stems brought to the lowercase n weight (edge offset); accents
  scaled only. One cell; half a cell for I-forms. The small-cap lookups run
  before locl, so Bulgarian т small-caps to Т, not M.
- pnum: a proportional 1 on the half cell, without its base serif (trimmed it
  read as l), flag kept. Other figures stay tabular: on a three-width grid
  they would gain nothing; tabular remains the default.
- Outline clean-up after rounding (no zero-length or duplicated segments).
- Italics for all eight weights, made the same way as Ferrum Mono's (10°
  oblique, strokes corrected to their upright thickness, widths 303 / 606 /
  909 unchanged). STAT table in every static.
- Web subsets (`fonts/webfonts/subset/`): latin, latin-ext, cyrillic,
  cyrillic-ext and symbols per weight with a unicode-range stylesheet.
- Į į ļ: the ogonek / comma below the baseline is moved with the narrow
  letter and no longer trimmed by the half cell (it was cut to a sliver);
  pulled in only where it would stick out of the cell.
- Variable fonts `fonts/variable/FerrumTrio[wght].ttf` and
  `FerrumTrio-Italic[wght].ttf` (+ WOFF2), wght 100–800, built from Ferrum
  Mono's variable masters with `trio.py --variable` (`scripts/variable.py`):
  localized forms, small caps and pnum included, all point-compatible.
  Unhinted.

## 1.001

- Wide letters re-made: stretched horizontally, then every edge moved along
  its normal so each stroke keeps its perpendicular thickness at its new
  slope. The 1.000 stretch added the width wherever there was little ink,
  which thickened bowls and diagonals (Ю, М, W up to +20%).
- Ж ж Җ җ (and Ӂ ӂ Ӝ ӝ, cv02) drawn anew for the wide cell: stem at full H / n
  weight, К-weight diagonals, the same stepped join.
- Cyrillic М gets the full stem weight like Latin M.
- i і ї: the dot set slightly left of the stem centre, against the flag (it
  read as drifting right); the ї dieresis kept inside the half cell.

## 1.000

Built from Ferrum Mono 1.002.

- Half cell (303): space and no-break space, I i l ı and their accented forms,
  І і Ї ї, `. , : ; ! | ' ’ ‘ ‚ ·`. Serifs trimmed symmetrically around the
  stem; accents and dots moved, not trimmed. ľ ŀ Ŀ ł stay one cell.
- One and a half cells (909): М Ш Щ Ю Ж Ы Љ Њ Җ, M W Æ Œ, their lowercase,
  accented forms and cv02 alternates. The extra width goes where the letter
  has little ink, so stems keep their thickness; m ш щ ы M Ш Щ Ы get the full
  n / H stem weight back.
- Kerning on by default (`kern`, from Ferrum Mono's ss20). ss02 (duospace) and
  ss03 (narrow space) dropped: Trio has both built in.
- Mark anchors follow the re-widthed letters.
- post.isFixedPitch 0, PANOSE proportion "modern". Font checkers that infer
  monospace from the share of one-cell glyphs (fontbakery opentype/monospace)
  flag Trio as a monospace font with wrong widths; that is expected for a
  quasi-proportional design and left as is.
