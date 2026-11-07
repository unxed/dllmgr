"""Normalize affected original contours before offsetting; no font installation."""
from pathlib import Path
import json
import sys
import fontforge

source, affected, output = sys.argv[1:]
font = fontforge.open(source)
for value in json.loads(Path(affected).read_text()):
    glyph = font[int(value[2:], 16)]
    advance = glyph.width
    if glyph.validate(True) & 4:
        glyph.removeOverlap()
    glyph.correctDirection()
    glyph.round()
    if glyph.validate(True) & 4:
        glyph.removeOverlap()
        glyph.correctDirection()
        glyph.round()
    glyph.width = advance
    if glyph.validate(True) & 12:
        raise RuntimeError('Original contour normalization failed: '+value)
font.generate(output, flags=('no-hints',))
font.close()
