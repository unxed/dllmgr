"""Straight-stem detection (candidate for the C port): a group of tall
columns (longest run of coverage >= 128 >= minrun rows, 16x wide raster),
0.35 px .. 0.3 em wide, counts as a stem only if in at least minrun rows the
ink run through its middle column starts and ends within TOL hi-res columns
of the group's edges (a straight vertical stroke; round bowls and slivers
fail)."""
import functools, numpy as np
from ftlab import LOAD_LIGHT
OS = 16
TOL = 2

@functools.lru_cache(maxsize=None)
def straight_stems(font, ch, tol=TOL, minw=0.35):
    r = font.render(ch, None, 'gray', LOAD_LIGHT, xscale=OS)
    if r is None: return ()
    a, left, top = r
    ink = a >= 128
    H, W = ink.shape
    minrun = max(3, (font.ppem * 245 + 500) // 1000)
    run = np.zeros(W, int)
    for c in range(W):
        best = cur = 0
        for v in ink[:, c]:
            cur = cur + 1 if v else 0; best = max(best, cur)
        run[c] = best
    tall = run >= minrun
    out = []; c = 0
    while c < W:
        if not tall[c]: c += 1; continue
        s = c
        while c < W and tall[c]: c += 1
        e = c
        if (e - s) * 10 > 3 * font.ppem * OS or (e - s) < minw * OS: continue
        mid = (s + e) // 2; good = 0; rows = []
        for y in range(H):
            if not ink[y, mid]: continue
            a0 = mid
            while a0 > 0 and ink[y, a0 - 1]: a0 -= 1
            b0 = mid
            while b0 < W - 1 and ink[y, b0 + 1]: b0 += 1
            b0 += 1
            if abs(a0 - s) <= tol and abs(b0 - e) <= tol: good += 1; rows.append(y)
        if good >= minrun:
            out.append(((left + s) / OS, (left + e) / OS, (top, tuple(rows)), good))
    return tuple(out)

if __name__ == '__main__':
    from measure import FONTS
    for size in (10, 11):
        f = FONTS[('regular', size)]
        for c in 'ContrasheocdpbmuklBHЯКлнИ':
            print(size, c, [(round(L, 2), round(R - L, 2)) for L, R, r, w in straight_stems(f, c)])
