"""
Rebuild ferrum-experimental fonts from ferrum-mono TTFs.

Usage (from repo root):
    python ferrum-experimental/scripts/build.py

Reads  : ferrum-mono/fonts/ttf/FerrumMono-*.ttf
         ferrum-mono/fonts/variable/FerrumMono*.ttf
Writes : ferrum-experimental/fonts/ttf/FerrumExperimental-*.ttf
         ferrum-experimental/fonts/webfonts/
         ferrum-experimental/fonts/variable/
         ferrum-experimental/fonts/nerd/   (NF copied as-is)
"""
import sys, os, shutil
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
MONO = ROOT / "ferrum-mono"
EXP  = ROOT / "ferrum-experimental"

TTF_OUT  = EXP / "fonts" / "ttf"
WOFF_OUT = EXP / "fonts" / "webfonts"
VAR_OUT  = EXP / "fonts" / "variable"
NF_OUT   = EXP / "fonts" / "nerd"

for d in [TTF_OUT, WOFF_OUT, VAR_OUT, NF_OUT]:
    d.mkdir(parents=True, exist_ok=True)

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))
_saved_argv = sys.argv[:]
sys.argv = ["arch.py", str(TTF_OUT)]
import arch as arch_mod
import contrast as cmod
sys.argv = _saved_argv

VERT = 0.024; HORZ = 0.090; ENERGY = 0.02; FAIR = 6000.0; CALM = 0.26

def apply(src_ttf: Path, dst: Path):
    shutil.copy2(src_ttf, dst)
    arch_mod.process(str(dst))
    cmod.VERT = VERT; cmod.HORZ = HORZ
    cmod.ENERGY = ENERGY; cmod.FAIR = FAIR; cmod.CALM = CALM
    f = TTFont(str(dst)); cmod.contrast(f); f.save(str(dst))

# static TTFs
print("=== static TTFs ===")
for src in sorted((MONO / "fonts" / "ttf").glob("FerrumMono-*.ttf")):
    dst = TTF_OUT / src.name.replace("FerrumMono-", "FerrumExperimental-")
    print(f"  {src.name}")
    apply(src, dst)

# WOFF2 from processed TTFs
print("\n=== WOFF2 ===")
weight_map = {
    "Thin": 100, "ExtraLight": 200, "Light": 300, "Regular": 400,
    "Medium": 500, "SemiBold": 600, "Bold": 700, "ExtraBold": 800,
}
for ttf in sorted(TTF_OUT.glob("FerrumExperimental-*.ttf")):
    dst = WOFF_OUT / ttf.name.replace(".ttf", ".woff2")
    f = TTFont(str(ttf)); f.flavor = "woff2"; f.save(str(dst))
    print(f"  {dst.name}")
css = ['/* Ferrum Experimental — webfonts */\n']
for name, w in weight_map.items():
    for suf, style in [(name, "normal"), (f"{name}Italic", "italic")]:
        fname = f"FerrumExperimental-{suf}.woff2"
        css.append(
            f'@font-face {{\n  font-family: "Ferrum Experimental";\n'
            f'  font-style: {style};\n  font-weight: {w};\n'
            f'  src: url("{fname}") format("woff2");\n}}\n'
        )
(WOFF_OUT / "ferrum-experimental.css").write_text("\n".join(css), encoding="utf-8")

# variable
print("\n=== variable ===")
for src in sorted((MONO / "fonts" / "variable").glob("FerrumMono*.ttf")):
    dst = VAR_OUT / src.name.replace("FerrumMono", "FerrumExperimental")
    print(f"  {src.name}")
    apply(src, dst)
    dst_w2 = VAR_OUT / dst.name.replace(".ttf", ".woff2")
    f2 = TTFont(str(dst)); f2.flavor = "woff2"; f2.save(str(dst_w2))

# NF — apply arch+contrast to text glyphs (icon glyphs are outside the glyph ranges touched)
print("\n=== NF ===")
for src in sorted((MONO / "fonts" / "nerd").glob("FerrumMonoNF-*.ttf")):
    dst = NF_OUT / src.name.replace("FerrumMonoNF-", "FerrumExperimentalNF-")
    print(f"  {src.name}")
    apply(src, dst)

print("\nDone. Run specimen.py to regenerate specimen.png.")
