#!/usr/bin/env python3
"""Check counters and disconnected ink components at 256 ppem, without hinting."""
import argparse
import json
from pathlib import Path
import freetype

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('candidate', type=Path)
parser.add_argument('affected', type=Path)
args = parser.parse_args()
codes = [int(value[2:], 16) for value in json.loads(args.affected.read_text())]


def components(face, code, ink=False):
    face.set_pixel_sizes(0, 256)
    face.load_char(chr(code), freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING |
                   freetype.FT_LOAD_NO_AUTOHINT | freetype.FT_LOAD_NO_BITMAP)
    bitmap = face.glyph.bitmap
    width, height, pixels = bitmap.width, bitmap.rows, bitmap.buffer
    seen, areas = set(), []

    def included(x, y):
        return (pixels[y * bitmap.pitch + x] >= 128) == ink

    for y in range(height):
        for x in range(width):
            if (x, y) in seen or not included(x, y):
                continue
            queue = [(x, y)]
            seen.add((x, y))
            area, border = 0, False
            while queue:
                xx, yy = queue.pop()
                area += 1
                border |= xx in (0, width - 1) or yy in (0, height - 1)
                for nx, ny in ((xx-1, yy), (xx+1, yy), (xx, yy-1), (xx, yy+1)):
                    if (0 <= nx < width and 0 <= ny < height and
                            (nx, ny) not in seen and included(nx, ny)):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if area >= 4 and (ink or not border):
                areas.append(area)
    return sorted(areas)


source, candidate = freetype.Face(str(args.source)), freetype.Face(str(args.candidate))
failures, counter_ratios, ink_ratios = [], [], []
for code in codes:
    for ink, label, minimum, ratios in ((False, 'counter', .1, counter_ratios),
                                       (True, 'ink component', .8, ink_ratios)):
        before, after = components(source, code, ink), components(candidate, code, ink)
        if len(before) != len(after):
            failures.append((f'U+{code:04X}', label, before, after))
        elif before:
            ratios.extend(a/b for a, b in zip(after, before))
            if any(a < b * minimum for a, b in zip(after, before)):
                failures.append((f'U+{code:04X}', label, before, after))
print(f'Checked {len(codes)} affected glyphs; counter/component failures: {len(failures)}')
for item in failures:
    print(item)
if counter_ratios:
    print(f'Minimum retained counter area ratio: {min(counter_ratios):.4f}')
if ink_ratios:
    print(f'Minimum retained ink-component area ratio: {min(ink_ratios):.4f}')
print('This raster topology check does not establish visual font quality.')
raise SystemExit(bool(failures))
