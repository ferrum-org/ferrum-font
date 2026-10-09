"""Ferrum Trio as variable fonts (wght 100-800): upright and italic.

    python3 variable.py PAPER_VAR GEIST_VAR WORK ../fonts/variable [--reuse]

Builds Ferrum Mono's variable masters first (../../ferrum-mono/scripts/
variable.py, same arguments), turns each into a Trio master with
trio.py --variable, and builds the variable font from those. Unhinted.
"""
import sys, os, glob, subprocess, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
MONO = os.path.join(HERE, "..", "..", "ferrum-mono", "scripts", "variable.py")
spec = importlib.util.spec_from_file_location("mono_variable", MONO)
mv = importlib.util.module_from_spec(spec); spec.loader.exec_module(mv)

if __name__ == "__main__":
    PAPER_VAR, GEIST_VAR, WORK, OUT = sys.argv[1:5]
    mono = os.path.join(WORK, "masters")
    if not ("--reuse" in sys.argv[5:] and len(glob.glob(os.path.join(mono, "*.ttf"))) == 8):
        mono = mv.masters(PAPER_VAR, GEIST_VAR, WORK)    # else: Mono's run left them there
    mv.same_kerning(sorted(glob.glob(os.path.join(mono, "*.ttf"))))
    trio = os.path.join(WORK, "trio-masters")
    os.makedirs(trio, exist_ok=True)
    for f in glob.glob(os.path.join(trio, "*.ttf")):
        os.remove(f)
    subprocess.run([sys.executable, "trio.py", mono, trio, "--variable"], cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    for italic in (False, True):
        src = mv.italic_masters(trio, os.path.join(WORK, "trio-masters-italic")) if italic else trio
        vf = mv.build(src, PAPER_VAR, "Ferrum Trio", "FerrumTrio", italic=italic)
        out = mv.save(vf, OUT, "FerrumTrio", italic)
        print(out, os.path.getsize(out) // 1024, "KB;", os.path.getsize(out[:-4] + ".woff2") // 1024, "KB woff2")
