# FONTLOG — Ferrum Mono

Ferrum Mono is the monospace typeface of the ferrum project. It is a modified
version of [Paper Mono](https://github.com/paper-design/paper-mono) (v1.000)
with Cyrillic adapted from [Geist Mono](https://github.com/vercel/geist-font)
(v1.700). Like both sources, it is released under the SIL Open Font License 1.1.

Ferrum Mono is not affiliated with or endorsed by Paper (Lost Coast Labs, Inc.)
or Vercel.

## 1.005

Note: the changes described here were developed for and applied in
**ferrum-experimental**. The Mono published binaries at this version do not
include them.

- Contrast parameters explored for Experimental (documented here for
  reference): VERT 0.016 → **0.024**, HORZ 0.048 → **0.090** (stronger pen
  angle, ~0.82× the stem on horizontals). Curvature-jump target raised
  0.18 → **0.26** (CALM), widening the bottom arches of round letters
  (о е р б ц etc.) so they no longer pinch in ExtraBold.
- `arch.py` diagonal tops (l and r): the flat horizontal terminal at the top
  of lowercase **l** and the arm shelf of lowercase **r** become a curved
  diagonal. In **l** the top-left corner becomes an off-curve guide at 62% of
  the ascender height, sweeping the top into a concave arc. In **r** the
  arm-shelf corner stays on-curve but its Y is lowered to 62% of the distance
  between the inner bay top and the shelf, creating a pointed diagonal without
  curvature artifacts at the shoulder. No points added or removed; variable
  masters stay compatible.

`arch.py` diagonal tops (l and r) and the contrast parameters above are
applied in ferrum-experimental; the Mono published binaries at this version
do not include them.

## 1.004

- Ferrum's own face, open terminals: every curved stroke end in letters and
  figures (c e s a g j 2 3 5 C G J S, с е з э ...) is cut across the stroke
  and 20° past square, so the forms open up like Akzidenz Grotesk's and the
  ends get sharp. Square ends of straight strokes (serifs, crossbars, stem
  feet) are unchanged. Built by moving points along the curve (`chisel.py`):
  no stubs are left, a guard reverts any cut that would cross the outline,
  and the variable masters replay the Regular's decisions, so they stay
  compatible.
- Humanist contrast (`contrast.py`), as from a broad pen held at 30°:
  verticals and descending diagonals (\) a little heavier, horizontals and
  ascending diagonals (/) thinner (about 0.88 of the stem in Regular), and
  round letters stressed back, thin at 11 and 5 o'clock. The outline is
  refitted to the exact offset curve with its curve energy in the fit, so the
  bowls run smoother than before (curvature jumps down by about a third);
  heights, dots and box drawing are untouched.

## 1.003

- ✓ ✔ ✗ ✘ ✕ ✖ (U+2713–2718) added for CLIs and test runners: strokes of
  the font's own stem weight (heavy forms up to 1.7x), one cell wide, the same
  centre lines in every weight (`symbols.py`).
- Localized forms (GSUB locl under 'cyrl'), following the modern Bulgarian
  set in Geologica, Montserrat and Commissioner:
  - Bulgarian (BGR): и й ѝ п т к д as Paper's u ŭ ù n m k g; л as ʌ; ш щ as
    ɯ (with the ц tail on щ); ц as u with the tail; ж and ю with the stem up
    to the ascender; з as ʒ; в with its upper bowl on the ascender; г as ƨ;
    Д as Δ on Д's feet; Л as Λ.
  - Serbian (SRB): б as δ. Macedonian (MKD): ѓ with a steeper acute.
  - Italic-only Serbian/Macedonian forms (г д п т) are not included: no italic.
- Build: locl.py after marks.py.
- Italics for all eight weights: a 10° oblique built by `oblique.py` from the
  finished uprights. After the shear every edge is moved along its normal so
  each stroke keeps its upright perpendicular thickness (measured within ±3%
  on stems, bowls and diagonals). Box drawing, block elements and private-use
  symbols stay upright. Advances unchanged (606). Mark anchors follow the
  slant; italic angle, caret slope, fsSelection / macStyle and RIBBI names
  (Regular–Italic, Bold–Bold Italic) set.
- STAT table (weight + italic) in every static, so uprights and italics are
  one family.
- Ferrum Mono NF (`fonts/nerd/`): Ferrum Mono with the Nerd Fonts symbols
  (v3.5.1, ~10,600 icons) for terminals. Icons one cell wide and centred on
  the line; Powerline separators stretched to the full cell and line so prompt
  segments join. Latin and Cyrillic glyphs, metrics and hinting identical to
  Ferrum Mono; the icons are unhinted. Icon licenses in
  `fonts/nerd/LICENSES.md`.
- Web subsets (`fonts/webfonts/subset/`): latin, latin-ext, cyrillic,
  cyrillic-ext and symbols per weight with a unicode-range stylesheet.
- Variable fonts `fonts/variable/FerrumMono[wght].ttf` and
  `FerrumMono-Italic[wght].ttf` (+ WOFF2): wght 100–800, named instances
  Thin…ExtraBold (Thin Italic…ExtraBold Italic), STAT with weight and italic
  axis values. Built from one master per static weight
  (`scripts/variable.py`): Latin from instances of Paper Mono's own variable
  font, Cyrillic and the localized forms through the same steps as the
  statics with point-compatible outlines (rebuilt letters kept as overlapping
  parts, no outline cleanup, fixed start points, kerning pairs aligned across
  masters). In the variable masters Serbian б drops ð's bar contour instead
  of cutting it out, and Bulgarian в raises its top bar point by point.
  The italic masters get oblique.py's shear and stroke correction point by
  point. Paper's Q with the bracketed tail comes back as a feature variation
  (rvrn) from about wght 738. Unhinted; smart dropout control in prep.

## 1.002

- Ж ж (and Җ җ): the diagonals step away from the stem on a short shelf, so
  the join stays open in the heavy weights instead of filling in. The same
  letters with the step spread wider are in `cv02`.
- ss20 kerning: pairs with the slab-serif I i l j are limited to −20 (LI, ГI,
  lj, fj were kerned up to −80 and nearly touched).
- OpenType feature lists sorted by tag (OTS warning).

## 1.001

- Cyrillic weight matched to the Latin in every weight: the Geist Mono source
  is now an instance of the variable font chosen per weight so that its stems
  equal Paper Mono's (Regular ≈ wght 433, ExtraBold ≈ 871), instead of the
  static weight of the same name (which was up to 9% light or 6% heavy).
  Lowercase bars (т г п …) and the three-stem ш щ ы are thickened where Geist's
  heavy weights have more contrast than Paper's, to match z and m.
- Lowercase Cyrillic sits exactly on Paper's x-height (509) in every weight;
  it used to grow to 521 in ExtraBold. Round letters overshoot like o (521 /
  −12), capitals like O.
- TrueType hinting: the whole font is autohinted (ttfautohint). The Cyrillic
  had no instructions and rendered blurry next to the hinted Latin on Windows.
- Contours of the 22 rebuilt letters (К Ж И Ч Ф and derived) turned clockwise;
  Geist-drawn outlines cleaned (overlaps, duplicate points).
- Combining marks attach to Cyrillic (stress marks: за́мок, И́ра); capitals use
  the .case marks; і ј drop the dot before a top mark. U+02BC (Ukrainian
  apostrophe) added.
- л no wider than н. Ф ф kept inside the cell in Bold / ExtraBold.
  Ў ў take Paper's breve (as Ŭ ŭ).
- Strictly monospaced: the 21 key-cap and arrow symbols that were 1.25 cells
  wide (⌘ ⌥ ⏎ ⇧ …) fit the cell; post.isFixedPitch set. Block elements
  (▀ ▄ █ …) span the full line height.
- Name table: Windows records only; version 1.001.

## 1.000

- Latin, figures and punctuation: unchanged from Paper Mono.
- Cyrillic (U+0400–U+052F) taken from Geist Mono and fitted to Paper Mono's
  metrics: 606-unit cell, x-height 509, ascender 747, descender −182.
  Letters drawn the same as Latin ones (А В Е О Р С Х а е о р с у х ё і …)
  reuse Paper Mono's Latin glyphs.
- Л л Д д narrowed; the tails of Д Ц Щ shortened to the lowercase depth.
- К к Ж ж И и Й й Ѝ ѝ Ӣ ӣ Ч ч Ф ф Қ қ Җ җ Ҷ ҷ rebuilt from Paper Mono's own
  shapes (K/k, H/n stems, U/u bowl, o).
- Cyrillic re-centred in the cell by optical side space, calibrated on Paper
  Mono's Latin.
- Pair kerning (~8,000 pairs per weight) added in stylistic set `ss20`,
  off by default so code keeps the monospace grid.
- `cyrl` script record added to GSUB and GPOS.
- Paper's logo glyph (U+F8FF) removed; Paper-branded name strings neutralised;
  vendor and designer URLs of the original authors removed from the name table.
- Family renamed to Ferrum Mono.
