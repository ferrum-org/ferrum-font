"""WOFF2 webfonts from the final TTFs."""
import sys, glob, os
from fontTools.ttLib import TTFont

SRC, DST = sys.argv[1], sys.argv[2]
for p in sorted(glob.glob(os.path.join(SRC, "*.ttf"))):
    f = TTFont(p); f.flavor = "woff2"
    out = os.path.join(DST, os.path.basename(p)[:-4] + ".woff2"); f.save(out)
    print(out, os.path.getsize(out) // 1024, "KB")
