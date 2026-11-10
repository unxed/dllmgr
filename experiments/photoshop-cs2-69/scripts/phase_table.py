"""#69 problem in numbers: every vertical stem of the lab's glyphs, rendered
at each of the three phases, binned by where its left edge lands within the
pixel (fraction of a px, after the phase shift). Per bin: median peak
darkness (sRGB, 1 = black) and ink per row (linear light, px) of the stem,
current agg vs the stem fix. Also "Contrast:" stem by stem at Photoshop's
placement."""
import sys, numpy as np
from measure import *
import measure, straight
glyph_stems = measure.glyph_stems = lambda font, ch, all_stems=False: straight.straight_stems(font, ch)  # the stems the fix treats
CHARS = sorted(set(''.join(WORDS)))

def stem_vals(font, ch, key, v):
    g = glyph_canvas(font, ch, 0, key, v)
    if g is None: return []
    a, gx, top = g
    ds, dl = darkness(to_pixels(a, v.mode, v.gamma))
    smap = stem_map(font, ch, key)
    spread = 0.5 + (2 / 3.0 if v.mode == 'rgb' else 0.0)
    out = []
    for L, R, (dtop, rows), wgt in glyph_stems(font, ch):
        Lp, Rp = smap(L), smap(R)
        cols = [x for x in range(ds.shape[1]) if Lp - spread - 1e-6 <= gx + x + 0.5 <= Rp + spread + 1e-6]
        rr = [r + (top - dtop) for r in rows if 0 <= r + (top - dtop) < ds.shape[0]]
        if not cols or not rr: continue
        out.append((Lp, R - L, float(np.median([ds[r, cols].max() for r in rr])),
                    float(np.median([dl[r, cols].sum() for r in rr]))))
    return out

def table(style, size, mode, alpha):
    f = FONTS[(style, size)]
    res = {}
    for name, keyf, v in [('agg', lambda s: ('shift', s), Variant('agg', mode)),
                          ('fix', lambda s: ('cwarp', s, alpha, True), Variant('fix', mode))]:
        bins = {b: [] for b in range(6)}
        for ch in CHARS:
            for ph in range(3):
                s = (ph * 64 + 1) // 3
                base = stem_vals(f, ch, ('shift', s), Variant('agg', mode))
                for (L0, w, _, _), (Lp, _, pk, ink) in zip(base, stem_vals(f, ch, keyf(s), v)):
                    b = int(((L0 % 1.0) * 6 + 0.5)) % 6  # bin by the UNFIXED left-edge phase
                    bins[b].append((pk, ink))
        res[name] = bins
    return res

if __name__ == '__main__':
    print('| style | size | mode | variant | ' + ' | '.join(f'edge at {b}/6 px' for b in range(6)) + ' | max-min peak | max-min ink |')
    print('|---' * 12 + '|')
    for style in ('regular', 'bold'):
        for size in (10, 11):
            for mode, alpha in (('rgb', 128), ('gray', 128)):
                res = table(style, size, mode, alpha)
                for name in ('agg', 'fix'):
                    bins = res[name]
                    pk = [np.median([p for p, i in bins[b]]) if bins[b] else np.nan for b in range(6)]
                    ik = [np.median([i for p, i in bins[b]]) if bins[b] else np.nan for b in range(6)]
                    cells = ' | '.join(f'{p:.2f} / {i:.2f} (n{len(bins[b])})' for b, (p, i) in enumerate(zip(pk, ik)))
                    print(f'| {style} | {size} | {mode} | {name} | {cells} | {np.nanmax(pk)-np.nanmin(pk):.2f} | {np.nanmax(ik)-np.nanmin(ik):.2f} |', flush=True)
