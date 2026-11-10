"""comparison sheet: rows = variants, columns = 1x (zoom), owner panel (scaling=exact), owner panel (scaling=smooth)"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from measure import *

def label_img(text, h, w):
    im = Image.new('RGB', (w, h), 'white'); d = ImageDraw.Draw(im)
    try: fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception: fnt = None
    d.text((4, max(0, h // 2 - 8)), text, fill='black', font=fnt)
    return np.asarray(im).astype(float)

def zoom(img, z): return np.repeat(np.repeat(img, z, 0), z, 1)

def cell(v, text, size, view, z):
    f = FONTS[('regular', size)]
    img, _, _, _ = compose(f, text, v)
    if view == '1x': return zoom(img, z)
    up = 2 if view == 'exact' else 'halftone'
    return zoom(as_seen(img, 1.6, 1, 0, up), z)

def sheet(variants, texts, out, size=11):
    cols = [('1x', 6), ('exact', 5), ('smooth', 5)]
    rows = []
    hdr = [label_img('', 22, 230)] + [label_img({'1x': '1x (x6)', 'exact': "owner's panel, scaling=exact (x5)",
                                                  'smooth': "owner's panel, scaling=smooth (x5)"}[c], 22, 10) for c, z in cols]
    for v in variants:
        cells = []
        for c, z in cols:
            parts = [cell(v, t, size, c, z) for t in texts]
            H = max(p.shape[0] for p in parts)
            row = np.concatenate([np.pad(p, ((0, H - p.shape[0]), (0, 12), (0, 0)), constant_values=255) for p in parts], 1)
            cells.append(row)
        H = max(c.shape[0] for c in cells)
        lab = label_img(f'{v.name} [{v.mode}]', H, 230)
        rows.append([lab] + [np.pad(c, ((0, H - c.shape[0]), (0, 0), (0, 0)), constant_values=255) for c in cells])
    widths = [max(r[i].shape[1] for r in rows) for i in range(len(rows[0]))]
    def pad(a, w): return np.pad(a, ((0, 4), (0, w - a.shape[1] + 16), (0, 0)), constant_values=255)
    lines = [np.concatenate([pad(h if i == 0 else label_img(['', '1x (x6)', "panel, scaling=exact (x5)", "panel, scaling=smooth (x5)"][i], 22, widths[i]), widths[i]) for i, h in enumerate(hdr)], 1)]
    for r in rows:
        lines.append(np.concatenate([pad(a, widths[i]) for i, a in enumerate(r)], 1))
    W = max(l.shape[1] for l in lines)
    img = np.concatenate([np.pad(l, ((0, 0), (0, W - l.shape[1]), (0, 0)), constant_values=255) for l in lines], 0)
    Image.fromarray(img.astype(np.uint8)).save(out)
    return img.shape

if __name__ == '__main__':
    vs = [Variant('agg (current)'), Snap('snap+full hint (rejected)', flags=LOAD_NORMAL), StemSnap('stem-snap warp'),
          Variant('ink-conserving e.2 g1.4', gamma=1.4, emb=0.2),
          Variant('agg (current)', 'rgb'), StemSnap('stem-snap warp', 'rgb'), Variant('ink e.2', 'rgb', emb=0.2)]
    print(sheet(vs, ['Contrast:', 'Channels'], sys.argv[1] if len(sys.argv) > 1 else 'sheet.png'))
