"""Keep nonzero-fill counters: resolve crossing contours before direction."""
from pathlib import Path
import json
import sys
import fontforge

source, affected, directory = sys.argv[1:]
out = Path(directory)
font = fontforge.open(source)
reports = []
for value in json.loads(Path(affected).read_text()):
    glyph = font[int(value[2:], 16)]
    before, advance = glyph.validate(True), glyph.width
    if before & 12:
        # correctDirection cannot choose the winding of a self-crossing
        # contour reliably. Doing it first destroys counters in в, д, ы.
        glyph.removeOverlap()
        glyph.correctDirection()
        glyph.round()
        if glyph.validate(True) & 4:
            # Rounding creates a tiny new crossing in U+04E9; resolve it once.
            glyph.removeOverlap()
            glyph.correctDirection()
            glyph.round()
    glyph.width = advance
    reports.append(dict(codepoint=value, before=before, after=glyph.validate(True)))
    (out/'progress.json').write_text(json.dumps(reports, indent=2))
font.generate(str(out/'generated.ttf'), flags=('no-hints',))
font.close()
print('done', len(reports), 'self-intersections', sum(bool(r['after'] & 4) for r in reports))
