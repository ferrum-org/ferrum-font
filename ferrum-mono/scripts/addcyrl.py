"""Add a 'cyrl' script record to GSUB/GPOS, copied from DFLT."""
import sys, glob, copy
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot
for p in sorted(glob.glob(sys.argv[1] + "/PaperMonoCyr-*.ttf")):
    f = TTFont(p)
    for tag in ("GSUB", "GPOS"):
        if tag not in f: continue
        sl = f[tag].table.ScriptList
        if any(r.ScriptTag == "cyrl" for r in sl.ScriptRecord): continue
        dflt = next(r for r in sl.ScriptRecord if r.ScriptTag == "DFLT")
        rec = ot.ScriptRecord(); rec.ScriptTag = "cyrl"; rec.Script = copy.deepcopy(dflt.Script)
        sl.ScriptRecord.append(rec); sl.ScriptRecord.sort(key=lambda r: r.ScriptTag); sl.ScriptCount = len(sl.ScriptRecord)
    f.save(p); print("cyrl added", p.split("/")[-1])
