"""Check label geometry in the real FastStone browser, separately from painting."""

import re
import sys
from pathlib import Path


observations = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
_, marker, grid = observations.partition("listview geometry: browser-grid\n")
if not marker:
    sys.exit("FastStone browser grid was not observed")

# The fixture starts with one folder and its first image. FastStone keeps
# these label strings outside the list-view's text, but needs both rectangles.
for item in (0, 1):
    match = re.search(rf"^  item {item} label=(-?\d+),(-?\d+),(-?\d+),(-?\d+)$", grid, re.MULTILINE)
    if not match:
        sys.exit(f"FastStone browser item {item} has no label rectangle")
    left, top, right, bottom = map(int, match.groups())
    if right <= left or bottom <= top + 1:
        sys.exit(f"FastStone browser item {item} has an empty label rectangle")
print("FastStone browser folder and image label rectangles are nonempty")
