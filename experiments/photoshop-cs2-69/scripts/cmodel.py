"""Bit-exact Python model of the proposed C change (stem-fix.diff):
soft stem snapping in freetype.c + phase choice (Viterbi) in dibdrv.

freetype.c, for an agg render at phase p (outline already shifted by
shift(p) = (p * 64 + 1) / 3):
  stems  = straight stems (straight.py): columns of the light-hinted outline,
           rasterised 16x wide, whose longest vertical run of coverage >= 128
           is >= max(3, 0.245 ppem) rows, grouped, 0.35 px .. 0.3 em wide, with
           >= as many rows whose ink run matches the group's edges +-1/8 px
  target = stem width rounded to whole px (>= 1), centre such that the left
           edge lands on a pixel edge (nearest)
  move   = alpha of the way (alpha in 1/256: rgb 128 = .5, grey 192 = .75)
  warp   = piecewise linear x map through the stem edges, constant shift
           outside; skipped when stems would collide or move > 0.75 px
dibdrv: each glyph may take its third, or one third less or more; Viterbi
  over the run minimises sum (left-edge error_i - right-edge error_{i-1})^2
  + 1/20 (mean error_i)^2, edge error = placed - ideal + warp displacement
  of the first / last stem edge; first and last glyph: a shifted third only
  with both edge errors within 0.5 px (ends=32)."""
import functools
import numpy as np
from straight import straight_stems

MAXMOVE = 48  # 0.75 px


def cdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


@functools.lru_cache(maxsize=None)
def knots(font, ch, shift64, alpha256, keepw=True):
    """[(old, new), ...] in 26.6 relative to the pen (whole px), or ()"""
    st = straight_stems(font, ch)
    out = []
    for L, R, rows, w in st:
        l = int(round(L * 64)) + shift64
        r = int(round(R * 64)) + shift64
        wd = r - l
        wf = max(64, (wd + 32) & ~63)
        c2 = l + r
        nlf = (cdiv(c2 - wf, 2) + 32) & ~63
        cf2 = 2 * nlf + wf
        W = wd if keepw else wd + cdiv(alpha256 * (wf - wd), 256)
        cen2 = c2 + cdiv(alpha256 * (cf2 - c2), 256)
        if abs(cen2 - c2) > 2 * MAXMOVE:
            return ()
        nl = cdiv(cen2 - W, 2)
        out.append((l, r, nl, nl + W))
    for a, b in zip(out, out[1:]):
        if b[0] <= a[1] or b[2] < a[3] + cdiv(alpha256 * 63, 256):
            return ()
    k = []
    for l, r, nl, nr in out:
        k += [(l, nl), (r, nr)]
    return tuple(k)


def warp_x(xs, kn):
    """xs: int array (26.6, already shifted by the phase)"""
    if not kn:
        return xs
    o = [a for a, b in kn]; n = [b for a, b in kn]
    out = np.empty_like(xs)
    for i, x in enumerate(xs):
        x = int(x)
        if x <= o[0]:
            y = x + n[0] - o[0]
        elif x >= o[-1]:
            y = x + n[-1] - o[-1]
        else:
            j = 0
            while x > o[j + 1]:
                j += 1
            y = n[j] + cdiv((x - o[j]) * (n[j + 1] - n[j]), o[j + 1] - o[j])
        out[i] = y
    return out


def xmap_cwarp(font, ch, shift64, alpha256, keepw=True):
    kn = knots(font, ch, shift64, alpha256, keepw)
    return lambda xs: warp_x(np.asarray(xs, np.int64) + shift64, kn)


def edges(font, ch, shift64, alpha256, keepw=True):
    kn = knots(font, ch, shift64, alpha256, keepw)
    if not kn:
        return 0, 0
    return kn[0][1] - kn[0][0], kn[-1][1] - kn[-1][0]


def place(font, text, alpha256, ends=32, wgap=20, keepw=True):
    """[(whole, shift64)] as the proposed dibdrv code chooses them"""
    lin_total = sum(font.metrics(c)[0] for c in text)
    app_total = 64 * sum(font.metrics(c)[1] for c in text)
    n = len(text)
    INF = 1 << 60
    opts = []
    lin = 0
    for c in text:
        ideal = cdiv(lin * app_total, lin_total)
        q = cdiv(ideal * 3 + (32 if ideal >= 0 else -32), 64)
        row = []
        for d in (-1, 0, 1):
            qq = q + d
            whole = qq // 3 if qq >= 0 else -((2 - qq) // 3)
            ph = qq - whole * 3
            s = (ph * 64 + 1) // 3
            el, er = edges(font, c, s, alpha256, keepw)
            pos = whole * 64 + s - ideal
            row.append((pos + el, pos + er, whole, s, d != 0))
        opts.append(row)
        lin += font.metrics(c)[0]

    def unary(i, o):
        if (i == 0 or i == n - 1) and o[4] and (ends == 0 or abs(o[0]) > ends or abs(o[1]) > ends):
            return INF  # ends == 0: first and last glyph keep their third
        m = cdiv(o[0] + o[1], 2)
        return m * m
    cost = [unary(0, o) for o in opts[0]]
    back = []
    for i in range(1, n):
        nc, bk = [], []
        for o in opts[i]:
            best, bj = None, 0
            for j, p in enumerate(opts[i - 1]):
                v = cost[j] + wgap * (o[0] - p[1]) ** 2
                if best is None or v < best:
                    best, bj = v, j
            nc.append(min(INF, best + unary(i, o))); bk.append(bj)
        cost = nc; back.append(bk)
    j = int(np.argmin(cost))
    path = [j]
    for i in range(n - 2, -1, -1):
        j = back[i][j]; path.append(j)
    path.reverse()
    return [(opts[i][path[i]][2], opts[i][path[i]][3]) for i in range(n)]
