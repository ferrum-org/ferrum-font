"""Rename Paper Mono Cyr -> Ferrum Mono (name table + file names)."""
import sys, glob, os
from fontTools.ttLib import TTFont

SRC, DST = sys.argv[1], sys.argv[2]
FAMILY, PS = "Ferrum Mono", "FerrumMono"
REVISION = "1.004"
VERSION = f"Version {REVISION}; based on Paper Mono 1.000 and Geist Mono 1.700"
COPYRIGHT = ("Copyright 2025 The Paper Mono Project Authors (https://github.com/paper-design/paper-mono). "
             "Copyright 2024 The Geist Project Authors (https://github.com/vercel/geist-font). "
             "Cyrillic adaptation, redrawn glyphs and ss20 kerning: 2026.")
DESIGNER = ("Paper Mono: Guido Ferreyra, Javier Quintana Godoy, Vladyslav Moroz. "
            "Geist Mono: Vercel in collaboration with basement.studio. Cyrillic adaptation: modified version.")
LICENSE = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
           "This license is available with a FAQ at: https://openfontlicense.org")
DESC = ("Monospace for the ferrum project. Based on Paper Mono, with Cyrillic adapted "
        "from Geist Mono. Not affiliated with or endorsed by Paper (Lost Coast Labs, Inc.) or Vercel.")
os.makedirs(DST, exist_ok=True)

for p in sorted(glob.glob(os.path.join(SRC, "PaperMonoCyr-*.ttf"))):
    weight = p.rsplit("-", 1)[1][:-4]
    ribbi = weight in ("Regular", "Bold")
    f = TTFont(p)
    n = f["name"]
    # Windows records only (no Mac duplicates); the original vendor and
    # designer URLs (IDs 8, 11, 12) are not carried over
    n.names = [r for r in n.names if r.platformID == 3 and (r.nameID >= 256 or r.nameID == 7)]
    pid, eid, lid = 3, 1, 0x409
    n.setName(COPYRIGHT, 0, pid, eid, lid)
    n.setName(FAMILY if ribbi else f"{FAMILY} {weight}", 1, pid, eid, lid)
    n.setName(weight if ribbi else "Regular", 2, pid, eid, lid)
    n.setName(f"{PS}-{weight};{REVISION}", 3, pid, eid, lid)
    n.setName(f"{FAMILY} {weight}", 4, pid, eid, lid)
    n.setName(VERSION, 5, pid, eid, lid)
    n.setName(f"{PS}-{weight}", 6, pid, eid, lid)
    n.setName(DESIGNER, 9, pid, eid, lid)
    n.setName(DESC, 10, pid, eid, lid)
    n.setName(LICENSE, 13, pid, eid, lid)
    n.setName("https://openfontlicense.org", 14, pid, eid, lid)
    if not ribbi:                          # 16/17 only where they differ from 1/2
        n.setName(FAMILY, 16, pid, eid, lid)
        n.setName(weight, 17, pid, eid, lid)
    # nothing of the old family name may survive
    for r in n.names:
        s = r.toUnicode()
        if "Paper Mono Cyr" in s or "PaperMonoCyr" in s:
            raise SystemExit(f"leftover name {r.nameID}: {s}")
    f["head"].fontRevision = float(REVISION)
    out = os.path.join(DST, f"{PS}-{weight}.ttf")
    f.save(out)
    print(out)
