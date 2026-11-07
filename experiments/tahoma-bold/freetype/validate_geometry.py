#!/usr/bin/env python3
"""Check candidate scope, point/advance invariants, bounds, and outline area."""
import json
import statistics
import sys
from pathlib import Path

from fontTools.pens.areaPen import AreaPen
from fontTools.ttLib import TTFont

source_path, candidate_path, regular_path, affected_path = map(Path, sys.argv[1:])
source, candidate, regular = (TTFont(p) for p in (source_path, candidate_path, regular_path))
codes = {int(value[2:], 16) for value in json.loads(affected_path.read_text())}

def area(font, code):
    name = font.getBestCmap()[code]
    pen = AreaPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return abs(pen.value)

changed = []
for name in source.getGlyphOrder():
    if source["glyf"][name].compile(source["glyf"], source) != candidate["glyf"][name].compile(candidate["glyf"], candidate):
        changed.append(name)
expected = {source.getBestCmap()[code] for code in codes}
point_errors, advance_errors, lsb_errors, y_errors = [], [], [], []
area_original, area_regular = [], []
for code in codes:
    name = source.getBestCmap()[code]
    old, new = source["glyf"][name], candidate["glyf"][name]
    old_coords = old.getCoordinates(source["glyf"])[0]
    new_coords = new.getCoordinates(candidate["glyf"])[0]
    if len(old_coords) != len(new_coords):
        point_errors.append(f"U+{code:04X}")
    if source["hmtx"][name][0] != candidate["hmtx"][name][0]:
        advance_errors.append(f"U+{code:04X}")
    if candidate["hmtx"][name][1] != new.xMin:
        lsb_errors.append(f"U+{code:04X}")
    if (old.yMin, old.yMax) != (new.yMin, new.yMax):
        y_errors.append(f"U+{code:04X}")
    area_original.append(area(candidate, code) / area(source, code))
    area_regular.append(area(candidate, code) / area(regular, code))

assert len(codes) == 66
assert not (set(changed) - expected), f"unexpected glyph records changed: {set(changed)-expected}"
assert len(changed) == 66
assert not point_errors, point_errors
assert not advance_errors, advance_errors
assert not lsb_errors, lsb_errors
assert not y_errors, y_errors

print(f"changed glyph records: {len(changed)} (expected affected set only)")
print(f"point-count mismatches: {len(point_errors)}")
print(f"advance mismatches: {len(advance_errors)}")
print(f"LSB != updated xMin: {len(lsb_errors)}")
print(f"y control-box mismatches: {len(y_errors)}")
print("area vs original bold min/median/max: " + "/".join(f"{v:.3f}" for v in (min(area_original), statistics.median(area_original), max(area_original))))
print("area vs regular min/median/max: " + "/".join(f"{v:.3f}" for v in (min(area_regular), statistics.median(area_regular), max(area_regular))))
print("head bbox: " + ", ".join(str(getattr(candidate["head"], k)) for k in ("xMin", "yMin", "xMax", "yMax")))
print("PS name/version: " + candidate["name"].getDebugName(6) + " / " + candidate["name"].getDebugName(5))
print(f"head.fontRevision: {candidate['head'].fontRevision:.3f}")
