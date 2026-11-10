#!/usr/bin/env python3
"""as-seen.py IN.png OUT.png [SCALE]: what a fractionally scaled panel shows
of a screenshot of the X screen. The owner's Cinnamon at 125 %: xrandr
Transform 1.6 with "filter: bilinear" (verified with `xrandr --verbose`,
2026-11-10, docs/owner-machine.md), i.e. the X server (pixman) takes, for
each panel pixel, ONE bilinear sample of the 3072x1728 frame at the mapped
pixel centre: no area averaging, so the result is sharp, not blurred; a
1-pixel detail survives or partly vanishes depending on where the sample
lands. SCALE is the transform (default 1.6)."""
import sys
import numpy as np
from PIL import Image

src = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float64)
t = float(sys.argv[3]) if len(sys.argv) > 3 else 1.6
h, w = src.shape[:2]
oh, ow = int(h / t), int(w / t)
# panel pixel centre (x + 0.5) -> source coordinate t * (x + 0.5); pixman samples
# between source pixel centres, hence the - 0.5
u = np.clip(t * (np.arange(ow) + 0.5) - 0.5, 0, w - 1)
v = np.clip(t * (np.arange(oh) + 0.5) - 0.5, 0, h - 1)
x0 = np.floor(u).astype(int); x1 = np.minimum(x0 + 1, w - 1); fx = (u - x0)[None, :, None]
y0 = np.floor(v).astype(int); y1 = np.minimum(y0 + 1, h - 1); fy = (v - y0)[:, None, None]
top = src[y0][:, x0] * (1 - fx) + src[y0][:, x1] * fx
bottom = src[y1][:, x0] * (1 - fx) + src[y1][:, x1] * fx
out = top * (1 - fy) + bottom * fy
Image.fromarray(np.clip(out + 0.5, 0, 255).astype(np.uint8)).save(sys.argv[2])
