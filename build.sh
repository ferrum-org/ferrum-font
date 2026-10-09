#!/bin/sh
# Full build of every Ferrum family, in dependency order.
#
#   ./build.sh PAPER_TTF_DIR GEIST_VARIABLE_TTF [SYMBOLS_NERD_FONT_MONO_TTF]
#
# PAPER_TTF_DIR       paper-design/paper-mono fonts/ttf
# GEIST_VARIABLE_TTF  vercel/geist-font (tag 1.7.0) fonts/GeistMono/variable/GeistMono[wght].ttf
# SYMBOLS_...         optional; nerd.py downloads Symbols Nerd Font Mono if omitted
# PAPER_VAR           Paper Mono's variable font for the variable builds
#                     (default: PAPER_TTF_DIR/../variable/PaperMono[wght].ttf)
# PYTHON              interpreter to use (default: python3); on Windows add -X utf8
set -e
PAPER="$1"; GEIST="$2"; SYMBOLS="$3"
PAPER_VAR="${PAPER_VAR:-$PAPER/../variable/PaperMono[wght].ttf}"
PY="${PYTHON:-python3}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --- Ferrum Mono -------------------------------------------------------------
M="$ROOT/ferrum-mono"
cd "$M/scripts"
rm -f ../fonts/ttf/*.ttf ../fonts/webfonts/*.woff2 ../fonts/nerd/*.ttf
$PY build.py    "$PAPER" "$GEIST" "$WORK/out"
$PY fix.py      "$WORK/out"
$PY redraw.py   "$WORK/out"
$PY respace.py  "$WORK/out" .
$PY kern.py     "$WORK/out" "$WORK/pairs.json"
$PY addcyrl.py  "$WORK/out"
$PY marks.py    "$WORK/out"
$PY locl.py     "$WORK/out"
$PY symbols.py  "$WORK/out"
$PY chisel.py   "$WORK/out"
$PY contrast.py "$WORK/out"
$PY rename.py   "$WORK/out" ../fonts/ttf
$PY clean.py    ../fonts/ttf
$PY hint.py     ../fonts/ttf
$PY oblique.py  ../fonts/ttf
$PY webfonts.py ../fonts/ttf ../fonts/webfonts
$PY subset.py   ../fonts/ttf ../fonts/webfonts/subset
$PY nerd.py     ../fonts/ttf ../fonts/nerd $SYMBOLS
$PY specimen.py ../fonts/ttf ../specimen.png
$PY kernsheet.py ../fonts/ttf "$WORK/pairs.json" ../kerning.png
rm -f ../fonts/variable/*.ttf ../fonts/variable/*.woff2
$PY variable.py "$PAPER_VAR" "$GEIST" "$WORK/var" ../fonts/variable

# --- Ferrum Trio (built from Ferrum Mono's uprights) ---------------------------
T="$ROOT/ferrum-trio"
cd "$T/scripts"
rm -f ../fonts/ttf/*.ttf ../fonts/webfonts/*.woff2
$PY trio.py     ../../ferrum-mono/fonts/ttf ../fonts/ttf
$PY hint.py     ../fonts/ttf
$PY oblique.py  ../fonts/ttf
$PY webfonts.py ../fonts/ttf ../fonts/webfonts
$PY subset.py   ../fonts/ttf ../fonts/webfonts/subset
$PY specimen.py ../fonts/ttf ../specimen.png ../../ferrum-mono/fonts/ttf
rm -f ../fonts/variable/*.ttf ../fonts/variable/*.woff2
$PY variable.py "$PAPER_VAR" "$GEIST" "$WORK/var" ../fonts/variable --reuse   # Mono's masters from above

echo "Ferrum fonts built."
