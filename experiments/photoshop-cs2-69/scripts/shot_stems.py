"""Stem darkness from stand screenshots (Photoshop's Brightness/Contrast dialog):
per label, x-height band = rows whose ink count >= half the maximum; darkness
(bg - v) / bg (bg = dialog face); a vertical stroke = run of columns dark
(> 0.2) in >= 80 % of the band rows (bowls and diagonals fail); its peak =
median over the band rows of the darkest pixel across the run +-1 column. CV over the strokes of the label; 'seen' = the same on
scripts/as-seen.py output (owner's 125 % panel)."""
import sys, numpy as np
from PIL import Image
LABELS = {'Brightness:': (1250, 515, 130, 45), 'Contrast:': (1250, 625, 110, 40)}
def strokes(img, box, scale=1.0):
    x, y, w, h = [int(round(v / scale)) for v in box]
    a = np.asarray(img.convert('L')).astype(float)[y:y + h, x:x + w]
    bg = np.median(a)
    d = np.clip((bg - a) / bg, 0, 1)
    ink = (d > 0.3).sum(1)
    band = np.nonzero(ink >= 0.5 * ink.max())[0]
    frac = (d[band] > 0.2).mean(0)  # vertical strokes: dark in >= 80 % of the band rows
    out, c = [], 0
    while c < len(frac):
        if frac[c] < 0.8: c += 1; continue
        s = c
        while c < len(frac) and frac[c] >= 0.8: c += 1
        out.append(float(np.median(d[band][:, max(0, s - 1):c + 1].max(1))))
    return out
for tag in sys.argv[1:]:
    for view, f, sc in (('frame', f'ps/{tag}-d.png', 1.0), ('seen', f'ps/{tag}-seen-full.png', 1.6)):
        img = Image.open(f)
        for lab, box in LABELS.items():
            st = strokes(img, box, sc)
            print(f'{tag} {view:5} {lab:12} strokes {len(st):2} peak min {min(st):.2f} max {max(st):.2f} cv {np.std(st)/np.mean(st):.3f} | ' + ' '.join(f'{v:.2f}' for v in st))
