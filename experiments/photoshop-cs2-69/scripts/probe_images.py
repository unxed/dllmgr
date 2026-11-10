"""before/after crops from the Wine probe (stem-words.exe, agg-rgb, Tahoma regular):
probe-1x.png  (x6 nearest; rows: size, before / after)
probe-seen.png (2x exact blocks -> scripts/as-seen.py (owner's 125 % panel) -> x4 nearest)"""
import subprocess, sys, numpy as np
from PIL import Image, ImageDraw
mode = sys.argv[1] if len(sys.argv) > 1 else 'agg-rgb'
A = np.asarray(Image.open(f'p-{mode}-s0.bmp').convert('RGB')); B = np.asarray(Image.open(f'p-{mode}-s1.bmp').convert('RGB'))
idx = [0, 1, 6, 20]  # Contrast:, Brightness:, Channels, Контраст:
def strip(img, size):
    parts = [img[4 + 16 * (k + (32 if size == 11 else 0)) - 2: 4 + 16 * (k + (32 if size == 11 else 0)) + 15, 2:78] for k in idx]
    return np.concatenate([np.pad(p, ((0, 0), (0, 4), (0, 0)), constant_values=255) for p in parts], 1)
def seen(img):
    big = np.repeat(np.repeat(img, 2, 0), 2, 1)
    Image.fromarray(big).save('_big.png')
    subprocess.run([sys.executable, '/home/claude/dllmgr/scripts/as-seen.py', '_big.png', '_seen.png'], check=True)
    return np.asarray(Image.open('_seen.png').convert('RGB'))
def z(a, k): return np.repeat(np.repeat(a, k, 0), k, 1)
def label(a, text):
    im = Image.fromarray(np.pad(a, ((14, 2), (0, 0), (0, 0)), constant_values=255)); ImageDraw.Draw(im).text((2, 1), text, fill=(200, 0, 0)); return np.asarray(im)
for name, f, k in (('1x', lambda a: a, 6), ('seen', seen, 4)):
    rows = []
    for size in (11, 10):
        for tag, img in (('current agg', A), ('DLLMGR69_STEM=1', B)):
            rows.append(label(z(f(strip(img, size)), k), f'Tahoma {size} px, {mode}, {tag}' + (" - as seen on the owner's 125 % panel" if name == 'seen' else ' - 1x, zoom x6')))
    W = max(r.shape[1] for r in rows)
    out = np.concatenate([np.pad(r, ((0, 6), (0, W - r.shape[1]), (0, 0)), constant_values=255) for r in rows], 0)
    Image.fromarray(out).save(f'probe-{mode}-{name}.png')
    print(f'probe-{mode}-{name}.png', out.shape)
