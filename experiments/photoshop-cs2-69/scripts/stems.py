"""Vertical stem detection on the design outline (vertically hinted, x exact)."""
import functools
import numpy as np
from ftlab import Font, LOAD_LIGHT

OS = 16  # horizontal oversampling for detection


@functools.lru_cache(maxsize=None)
def glyph_stems(font, ch, all_stems=False):
    """list of (L, R, rows, weight): stem edges in px from the glyph origin,
    rows = bitmap rows counted down from the glyph's top edge (y = top - row),
    as (top, [rows]); weight = stem height in px."""
    r = font.render(ch, None, 'gray', LOAD_LIGHT, xscale=OS)
    if r is None:
        return ()
    a, left, top = r
    cov = a / 255.0
    ink = a >= 128  # as the C port: 8-bit coverage >= 128
    H, W = ink.shape
    # longest vertical run per hi-res column
    run = np.zeros(W, int)
    for c in range(W):
        best = cur = 0
        for v in ink[:, c]:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        run[c] = best
    minrun = max(3, (font.ppem * 245 + 500) // 1000)  # ~0.45 x-height of Tahoma
    cols = run >= minrun
    stems = []
    c = 0
    while c < W:
        if not cols[c]:
            c += 1
            continue
        s = c
        while c < W and cols[c]:
            c += 1
        e = c  # [s, e) hi-res columns
        width = (e - s) / OS
        if (e - s) * 10 > 3 * font.ppem * OS:  # wider than 0.3 em: not a stem
            continue
        L = (left + s) / OS
        R = (left + e) / OS
        mid = (s + e) // 2
        rows = []
        for y in range(H):
            if not ink[y, mid]:
                continue
            row = ink[y]
            # ink run through the stem in this row
            a0 = mid
            while a0 > 0 and row[a0 - 1]:
                a0 -= 1
            b0 = mid
            while b0 < W - 1 and row[b0 + 1]:
                b0 += 1
            b0 += 1
            if a0 < s - 2 or b0 > e + 2:
                continue  # joins another stroke here
            lo, hi = max(0, s - int(2.2 * OS)), min(W, e + int(2.2 * OS))
            other = np.concatenate([cov[y, lo:max(lo, a0 - 1)], cov[y, min(hi, b0 + 1):hi]])
            if other.size and other.max() > 0.05:
                continue
            rows.append(y)
        if all_stems or len(rows) >= 2:
            stems.append((L, R, (top, tuple(rows)), max(1, len(rows))))
    return tuple(stems)


if __name__ == '__main__':
    from ftlab import REG, BOLD
    for path in (REG, BOLD):
        for ppem in (10, 11):
            f = Font(path, ppem)
            for ch in 'ConstrahiBgukdlpyHLPvwmИКлн':
                st = glyph_stems(f, ch)
                print(path[-11:], ppem, ch, [(round(L, 2), round(R - L, 2), len(r[1])) for L, R, r, w in st])
