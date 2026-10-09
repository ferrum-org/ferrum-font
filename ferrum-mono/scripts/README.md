# Building Ferrum Mono

Sources: Paper Mono 1.000 (`paper-design/paper-mono`, `fonts/ttf`) and the
variable Geist Mono 1.700 (`vercel/geist-font`, tag `1.7.0`,
`fonts/GeistMono/variable/GeistMono[wght].ttf`).

```sh
pip install fonttools skia-pathops numpy brotli ttfautohint-py

python3 build.py    PAPER_TTF GEIST_VAR out   # Paper Latin + Geist Cyrillic, weight-matched and fitted to Paper metrics
python3 fix.py      out                       # л Л Д narrower, Д Ц Щ tails shorter, outlines cleaned
python3 redraw.py   out                       # К Ж И Ч Ф Ў and derived letters rebuilt
python3 respace.py  out .                     # Cyrillic re-centred in the cell
python3 kern.py     out pairs.json            # pair kerning in ss20 (pairs.json: report for kernsheet.py)
python3 addcyrl.py  out                       # 'cyrl' script record
python3 marks.py    out                       # stress marks on Cyrillic, U+02BC
python3 locl.py     out                       # Bulgarian / Serbian / Macedonian forms (locl)
python3 symbols.py  out                       # ✓ ✔ ✗ ✘ ✕ ✖ for CLIs and test runners
python3 chisel.py   out                       # open terminals: curved stroke ends cut across the stroke, +20°
python3 contrast.py out                       # humanist contrast: pen axis 30°, fitted with curve energy
python3 rename.py   out ../fonts/ttf          # family name -> Ferrum Mono, version, name table
python3 clean.py    ../fonts/ttf              # Paper logo out, strict monospace, block elements, ss20 label
python3 hint.py     ../fonts/ttf              # ttfautohint, Latin and Cyrillic alike
python3 oblique.py  ../fonts/ttf              # italics (10° oblique, stroke-corrected) + STAT
python3 webfonts.py ../fonts/ttf ../fonts/webfonts
python3 specimen.py ../fonts/ttf ../specimen.png  # needs skia-python, uharfbuzz
python3 kernsheet.py ../fonts/ttf pairs.json ../kerning.png
python3 subset.py   ../fonts/ttf ../fonts/webfonts/subset   # per-script WOFF2 + unicode-range CSS
python3 nerd.py     ../fonts/ttf ../fonts/nerd [SymbolsNerdFontMono-Regular.ttf]  # Ferrum Mono NF

# variable fonts, upright + italic (Paper Mono's own variable font as the Latin source)
python3 variable.py PAPER_VAR GEIST_VAR work ../fonts/variable
```

`variable.py` builds one master per static weight with the same scripts, run
so that the masters stay point-compatible: Latin from instances of
`fonts/variable/PaperMono[wght].ttf` (outlines still overlapping), `fix.py`
and `redraw.py` with `--variable` (no outline cleanup; rebuilt letters as
overlapping parts with fixed start points). The kerning pair lists are then
made identical (0 where a weight has none) and varLib builds the font.

`build.py` picks, for every Paper weight, the Geist instance whose stems match
Paper's (Regular ≈ wght 433, ExtraBold ≈ 871), then thickens Geist's lowercase
bars and the three-stem ш щ ы where Geist's heavy weights have more contrast
than Paper.

`spacing.py` is a helper used by `respace.py`. The intermediate files in `out`
are still named `PaperMonoCyr-*`; `rename.py` writes the final `FerrumMono-*`.
On Windows run Python with `-X utf8`.
