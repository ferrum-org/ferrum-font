# FONTLOG — Ferrum Experimental

Ferrum Experimental is Ferrum Mono with two post-processing stages applied
on top of the standard build:

1. **Diagonal ascender tops** (`arch.py`): the flat horizontal terminal of
   lowercase **l** and the arm shelf of **r** become curved diagonals.
2. **Stronger humanist contrast** (`contrast.py`): VERT 0.024, HORZ 0.090,
   CALM 0.26 — heavier verticals, thinner horizontals, wider bottom arches on
   round letters (о е р б ц etc.).

Fonts are otherwise identical to Ferrum Mono. Same metrics, same features,
same cell width. Built from Ferrum Mono 1.004 binaries with post-processing.

## Build

```
python -I ferrum-mono/scripts/arch.py     <ttf>
python -I ferrum-mono/scripts/contrast.py <ttf>   # VERT=0.024 HORZ=0.090 CALM=0.26
```

Or run `build_experimental.py` in the repo root.
