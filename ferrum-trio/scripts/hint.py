"""TrueType hinting for Latin and Cyrillic alike (ttfautohint), in place.
The Cyrillic built from Geist carries no instructions of its own; without this
step it renders blurry next to the hinted Latin on Windows (ClearType)."""
import sys, glob, os, subprocess

for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.ttf"))):
    subprocess.run([sys.executable, "-m", "ttfautohint", "--composites", "--windows-compatibility",
                    "--default-script=latn", "--fallback-script=latn", p, p + ".tmp"], check=True)
    os.replace(p + ".tmp", p)
    print("hinted", p)
