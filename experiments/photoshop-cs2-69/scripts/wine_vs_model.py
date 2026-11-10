"""Wine probe (stem-words.exe bmp) vs the Python model (measure.py), line by line:
best alignment, then max |diff| and number of differing pixels (sRGB 0..255)."""
import sys, numpy as np
from PIL import Image
from measure import *
WORDS32 = WORDS
def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(int)
def lines(img):
    for k in range(128):
        y = 4 + 16 * k
        yield k, img[y - 4:y + 16, :]
def model(k, v):
    style = 'bold' if k // 64 else 'regular'; size = 10 + (k // 32) % 2
    img, pl, base, margin = compose(FONTS[(style, size)], WORDS32[k % 32], v)
    return img.astype(int)
def compare(path, v):
    img = load(path); worst = 0; ndiff = 0; bad = []
    for k, strip in lines(img):
        m = model(k, v)
        best = None
        for dy in range(0, strip.shape[0] - m.shape[0] + 1):
            for dx in range(0, 8):
                win = strip[dy:dy + m.shape[0], dx:dx + m.shape[1]]
                d = np.abs(win - m).max()
                if best is None or d < best[0]:
                    best = (d, int((np.abs(win - m).max(2) > 0).sum()), dy, dx)
        worst = max(worst, best[0]); ndiff += best[1]
        if best[0] > 2: bad.append((k, WORDS32[k % 32], best))
    return worst, ndiff, bad
if __name__ == '__main__':
    for path, mode, kind in [('p-agg-rgb-s0.bmp', 'rgb', 0), ('p-agg-rgb-s1.bmp', 'rgb', 128),
                             ('p-agg-s0.bmp', 'gray', 0), ('p-agg-s1.bmp', 'gray', 192)]:
        v = Variant('agg', mode) if not kind else CWarp('stem', mode, alpha=kind, ends=0)
        w, n, bad = compare(path, v)
        print(path, 'max |diff|', w, 'pixels differing', n, 'lines off by >2:', len(bad), bad[:4], flush=True)
