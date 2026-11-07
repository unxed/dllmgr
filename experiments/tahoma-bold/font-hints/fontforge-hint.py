"""Run with FontForge embedded Python, not python3."""
import json
import sys
import fontforge
source, affected, mode, output = sys.argv[1:]
f = fontforge.open(source)
f.selection.none()
if mode == "all":
    f.selection.all()
else:
    for code in json.load(open(affected)):
        f.selection.select(("more", "unicode"), int(code[2:], 16))
f.cvt = ()
for glyph in f.selection.byGlyphs:
    print("autoHint", glyph.glyphname, flush=True)
    glyph.autoHint()
print("autoInstr", mode, flush=True)
f.autoInstr()
print("generate", mode, flush=True)
f.generate(output)
f.close()
