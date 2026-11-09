#!/usr/bin/env python3
"""#36: count whitish fringe pixels of the splash feather outside the card.
fringe.py SHOT.png [x0 y0 x1 y1 card_x card_y]: area around the feather; card top-left."""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB')
x0, y0, x1, y1, cx, cy = map(int, sys.argv[2:8]) if len(sys.argv) > 7 else (860, 300, 1160, 600, 906, 360)
px = im.load()
hits = []
for y in range(y0, y1):
    for x in range(x0, x1):
        if x >= cx and y >= cy:
            continue  # on the card
        r, g, b = px[x, y]
        if min(r, g, b) > 165 and max(r, g, b) - min(r, g, b) < 60:
            hits.append((x, y))
print(len(hits), hits[:12])
