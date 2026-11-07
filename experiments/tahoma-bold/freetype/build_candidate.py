#!/usr/bin/env python3
"""Apply FreeType's fixed-point outline emboldening to the measured Tahoma glyphs.

Only existing outline points are changed. Glyph topology, advances, and all
other glyph outlines remain from the original Wine 11.0 font.
"""
import json
import math
import sys
from pathlib import Path

import freetype
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.areaPen import AreaPen

SOURCE = Path(sys.argv[1])
AFFECTED = Path(sys.argv[2])
OUTPUT = Path(sys.argv[3])
STRENGTH = 120
HORIZONTAL_MARGIN = 16
SCALE = 64

codes = [int(value.removeprefix("U+"), 16) for value in json.loads(AFFECTED.read_text())]
font = TTFont(SOURCE)
cmap = font.getBestCmap()
face = freetype.Face(str(SOURCE))
if face.units_per_EM != font["head"].unitsPerEm:
    raise SystemExit("FreeType and fontTools disagree about units per em")

report = []
for code in codes:
    name = cmap[code]
    glyph = font["glyf"][name]
    if glyph.isComposite():
        raise SystemExit(f"{code:04X} unexpectedly uses a composite outline")
    original_points = list(glyph.coordinates)
    original_count = len(original_points)
    original_advance = font["hmtx"][name][0]
    glyph.recalcBounds(font["glyf"])
    old_box = (glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax)

    face.load_char(chr(code), freetype.FT_LOAD_NO_SCALE | freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
    outline = face.glyph.outline
    if outline.n_points != original_count:
        raise SystemExit(f"U+{code:04X}: FreeType point count differs from fontTools")
    before = [(round(x), round(y)) for x, y in outline.points]
    if before != [(int(x), int(y)) for x, y in original_points]:
        raise SystemExit(f"U+{code:04X}: FreeType point order differs from source glyf")

    matrix = freetype.FT_Matrix(SCALE << 16, 0, 0, SCALE << 16)
    freetype.FT_Outline_Transform(freetype.byref(outline._FT_Outline), freetype.byref(matrix))
    error = freetype.FT_Outline_EmboldenXY(
        freetype.byref(outline._FT_Outline), STRENGTH * SCALE, STRENGTH * SCALE
    )
    if error:
        raise SystemExit(f"U+{code:04X}: FT_Outline_EmboldenXY failed with error {error}")
    emboldened = [(x / SCALE, y / SCALE) for x, y in outline.points]
    x0, y0, x1, y1 = outline.get_cbox().xMin / SCALE, outline.get_cbox().yMin / SCALE, outline.get_cbox().xMax / SCALE, outline.get_cbox().yMax / SCALE
    if x1 <= x0 or y1 <= y0:
        raise SystemExit(f"U+{code:04X}: invalid emboldened outline bounds")

    # Retain the original vertical extent and baseline using a deterministic
    # affine y fit, then fit/center horizontally without changing advance.
    y_scale = (old_box[3] - old_box[1]) / (y1 - y0)
    y_shift = old_box[1] - y0 * y_scale
    width = x1 - x0
    available = max(1, original_advance - 2 * HORIZONTAL_MARGIN)
    x_scale = min(1.0, available / width)
    x_shift = (original_advance - width * x_scale) / 2 - x0 * x_scale
    transformed = [(int(round(x * x_scale + x_shift)), int(round(y * y_scale + y_shift))) for x, y in emboldened]
    if len(transformed) != original_count:
        raise SystemExit(f"U+{code:04X}: point count changed")
    glyph.coordinates = GlyphCoordinates(transformed)
    glyph.recalcBounds(font["glyf"])
    # Instructions were authored for the old coordinates; leave these changed
    # glyphs unhinted instead of executing stale point movement instructions.
    glyph.program = Program()
    font["hmtx"][name] = (original_advance, glyph.xMin)

    pen = AreaPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    new_area = abs(pen.value)
    report.append({
        "codepoint": f"U+{code:04X}", "glyph": name,
        "points_before": original_count, "points_after": len(glyph.coordinates),
        "advance_before": original_advance, "advance_after": font["hmtx"][name][0],
        "bbox_before": list(old_box),
        "bbox_after": [glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax],
        "area_after": new_area,
        "horizontal_scale": x_scale, "vertical_scale": y_scale,
    })

# Assign a distinct identity while retaining family/style selection.
def set_name(name_id, value):
    for item in font["name"].names:
        if item.nameID == name_id:
            try:
                item.string = value.encode(item.getEncoding())
            except (LookupError, UnicodeEncodeError):
                item.string = value.encode("utf-16-be")

set_name(3, "WineTahomaBold-Cyrillic-5")
set_name(5, "Version 0.005; FreeType outline emboldening")
set_name(6, "WineTahomaBoldCyrillic005")
font["head"].fontRevision = 0.005
# Keep the TTF global bounds consistent with the changed outline extrema.
for glyph in font["glyf"].glyphs.values():
    if hasattr(glyph, "numberOfContours"):
        glyph.recalcBounds(font["glyf"])
bounded = [g for g in font["glyf"].glyphs.values() if hasattr(g, "xMin")]
font["head"].xMin = min(g.xMin for g in bounded)
font["head"].yMin = min(g.yMin for g in bounded)
font["head"].xMax = max(g.xMax for g in bounded)
font["head"].yMax = max(g.yMax for g in bounded)
font.recalcTimestamp = False
font.save(OUTPUT)
Path(str(OUTPUT) + ".geometry.json").write_text(json.dumps(report, indent=2) + "\n")
print(f"wrote {OUTPUT}; changed {len(report)} glyphs; strength={STRENGTH}; point counts and advances preserved")
