import sys, numpy as np
from PIL import Image
from measure import *
def strip(v, text, size=11, style='regular'):
    f = FONTS[(style, size)]
    img, pl, base, m = compose(f, text, v)
    return img
def zoom(img, z): return np.repeat(np.repeat(img, z, 0), z, 1)
rows = []
text = sys.argv[1] if len(sys.argv) > 1 else 'Contrast:'
for v in [Variant('agg', 'gray'), Variant('agg', 'rgb')]:
    img = strip(v, text)
    rows.append(zoom(img, 10))
    for xo in range(4):
        s = as_seen(img, 1.6, xo, 0)
        rows.append(zoom(s, 8))
W = max(r.shape[1] for r in rows)
out = np.full((sum(r.shape[0] + 6 for r in rows), W, 3), 255.0)
y = 0
for r in rows:
    out[y:y + r.shape[0], :r.shape[1]] = r; y += r.shape[0] + 6
Image.fromarray(out.astype(np.uint8)).save('look.png')
