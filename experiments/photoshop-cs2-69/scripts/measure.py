#!/usr/bin/env python3
"""#69 stem lab: variants of glyph placement / stem treatment, measured.

Per variant, mode (gray|rgb), size (10|11), style (regular|bold):
  stems : peak darkness (sRGB) and ink per px of stem width (linear light)
          of every detected vertical stem -> CV (std/mean) and range
  space : pair gap error from coverage centroids vs the exact (unquantised)
          ideal placement scaled to the app width, RMS and max |err| in px
  width : run ink extent minus the ideal ink extent, mean |diff| px
Same after the owner's panel view (2x blocks, bilinear 1/1.6), stems only,
averaged over 4 horizontal sampling phases."""
import ctypes, functools, json, sys
import numpy as np
import freetype
from ftlab import (Font, REG, BOLD, LOAD_LIGHT, LOAD_NORMAL, agg_place, run_totals,
                   ideal_positions, to_pixels, srgb_to_lin, as_seen, _lib)
from stems import glyph_stems

WORDS_EN = ["Contrast:", "Brightness:", "Opacity:", "Background", "History", "Layers",
            "Channels", "Preview", "Fill:", "Lock:", "Normal", "Brushes", "Histogram",
            "Navigator", "Info", "Paths", "Actions", "Swatches", "Color", "Styles"]
WORDS_RU = ["Контраст:", "Яркость:", "Непрозрачность:", "Слои", "История", "Каналы",
            "Заливка:", "Навигатор", "Кисти", "Цвет", "Стили", "Контуры"]
WORDS = WORDS_EN + WORDS_RU

_lib.FT_Outline_EmboldenXY.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_long]


# ---------------------------------------------------------------- rendering
@functools.lru_cache(maxsize=200000)
def render_glyph(font, ch, key, mode, flags, emb):
    """key: tuple (kind, args) describing the x map; cached"""
    xfun = XMAPS[key[0]](font, ch, *key[1:])
    f = font.face
    f.load_glyph(font.gid(ch), flags)
    slot = f.glyph._FT_GlyphSlot
    ol = slot.contents.outline
    n = ol.n_points
    if n == 0:
        return None
    if emb:
        _lib.FT_Outline_EmboldenXY(ctypes.addressof(ol), int(round(emb * 64)), 0)
        # keep the stems centred where they were: EmboldenXY grows to the right
        for i in range(n):
            ol.points[i].x -= int(round(emb * 32))
    xs = np.array([ol.points[i].x for i in range(n)], np.int64)
    xs = np.asarray(np.round(xfun(xs)), np.int64)
    for i in range(n):
        ol.points[i].x = int(xs[i])
    rm = freetype.FT_RENDER_MODE_LCD if mode == 'rgb' else freetype.FT_RENDER_MODE_NORMAL
    assert not freetype.raw.FT_Render_Glyph(slot, rm)
    bm = f.glyph.bitmap
    if bm.rows == 0 or bm.width == 0:
        return None
    a = np.array(bm.buffer, np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width] / 255.0
    if mode == 'rgb':
        a = a.reshape(bm.rows, bm.width // 3, 3)
    return a, f.glyph.bitmap_left, f.glyph.bitmap_top


def xmap_shift(font, ch, s64):
    return lambda xs: xs + s64


def stem_knots(font, ch, s64, grid, tol, minw, goff=0.0):
    """knots (old, new) in 26.6 that snap stem edges of ch, placed at local
    shift s64, to a grid of `grid` px (offset goff); a stem moves at most tol px"""
    knots = []
    for L, R, rows, w in glyph_stems(font, ch):
        Lp, Rp = L + s64 / 64.0, R + s64 / 64.0
        wid = R - L
        W = max(minw, round(wid / grid) * grid)
        c = (Lp + Rp) / 2
        nL = round((c - W / 2 - goff) / grid) * grid + goff
        # both rounding choices: the nearer one
        if abs((nL + W / 2) - c) > tol:
            continue
        knots.append((Lp, nL))
        knots.append((Rp, nL + W))
    knots.sort()
    good = []
    for o, nw in knots:  # keep monotone
        if good and (nw <= good[-1][1] or o <= good[-1][0]):
            return []
        good.append((o, nw))
    return good


def xmap_stems(font, ch, s64, grid, tol, minw, goff=0.0):
    knots = stem_knots(font, ch, s64, grid, tol, minw, goff)

    def f(xs):
        x = xs / 64.0 + s64 / 64.0
        if not knots:
            return x * 64
        o = np.array([k[0] for k in knots]); nw = np.array([k[1] for k in knots])
        y = np.interp(x, o, nw)
        y = np.where(x < o[0], x + (nw[0] - o[0]), y)
        y = np.where(x > o[-1], x + (nw[-1] - o[-1]), y)
        return y * 64
    return f


XMAPS = {'shift': xmap_shift, 'stems': xmap_stems}


def stem_map(font, ch, key):
    """design px -> placed px relative to whole (for stems)"""
    f = XMAPS[key[0]](font, ch, *key[1:])
    return lambda x: float(f(np.array([x * 64.0]))[0]) / 64.0


# ------------------------------------------------------------- placements
def thirds_place(font, text, step=3):
    lin_total, app_total = run_totals(font, text)
    out, lin = [], 0
    for c in text:
        ideal = int(lin * app_total / lin_total)
        q = int((ideal * step + 32) / 64)
        whole = q // step
        phase = q - whole * step
        out.append((whole, (phase * 64 + step // 2) // step))
        lin += font.metrics(c)[0]
    return out


def sharpness(font, ch, s64, mode, flags):
    r = render_glyph(font, ch, ('shift', s64), mode, flags, 0)
    if r is None:
        return 0.0
    a = r[0]
    if mode == 'rgb':
        a = a.mean(2)
    return float((a * a).sum() / max(1e-9, a.sum()))


class Variant:
    name = ''
    mode = 'gray'
    gamma = 2.2
    flags = LOAD_LIGHT
    emb = 0.0

    def __init__(self, name, mode='gray', **kw):
        self.name, self.mode = name, mode
        self.__dict__.update(kw)

    def place(self, font, text):
        """list of (whole_px, key)"""
        return [(w, ('shift', s)) for w, s in thirds_place(font, text, getattr(self, 'step', 3))]


class Snap(Variant):
    def place(self, font, text):
        return [(int(np.floor(p + 0.5)), ('shift', 0)) for p in ideal_positions(font, text)]


class SharpPhase(Variant):
    """pick, per glyph, among the thirds within `reach` thirds of the agg
    choice the one whose bitmap is sharpest (sum c^2 / sum c), minus a
    penalty per third of displacement; Viterbi over the run keeps the
    displacement of neighbours from adding up in one gap"""
    reach = 1
    lam = 0.02
    gap = 0.04

    def place(self, font, text):
        base = thirds_place(font, text, 3)
        cands = []
        for (w, s), c in zip(base, text):
            q = w * 3 + (s * 3 + 32) // 64
            opts = []
            for d in range(-self.reach, self.reach + 1):
                qq = q + d
                ww, ph = qq // 3, qq % 3
                s64 = (ph * 64 + 1) // 3
                score = sharpness(font, c, s64, self.mode, self.flags) - self.lam * abs(d)
                opts.append((d, ww, s64, score))
            cands.append(opts)
        # Viterbi: maximise sum score - gap * (d_i - d_{i-1})^2
        n = len(text)
        best = [[o[3] for o in cands[0]]]
        back = []
        for i in range(1, n):
            row, bk = [], []
            for o in cands[i]:
                vals = [best[-1][j] - self.gap * (o[0] - p[0]) ** 2 for j, p in enumerate(cands[i - 1])]
                j = int(np.argmax(vals))
                row.append(vals[j] + o[3]); bk.append(j)
            best.append(row); back.append(bk)
        j = int(np.argmax(best[-1]))
        path = [j]
        for i in range(n - 2, -1, -1):
            j = back[i][j]; path.append(j)
        path.reverse()
        return [(cands[i][path[i]][1], ('shift', cands[i][path[i]][2])) for i in range(n)]


class StemSnap(Variant):
    """keep the agg pen position (thirds), warp the outline so that stem
    edges land on the grid (1 px grey, 1/3 px rgb), moving a stem at most
    tol px; the advance stays fractional"""
    grid = 1.0
    tol = 0.5
    minw = 1.0

    def place(self, font, text):
        return [(w, ('stems', s, self.grid, self.tol, self.minw, getattr(self, 'goff', 0.0)))
                for w, s in thirds_place(font, text, 3)]


# ---------------------------------------------------------------- measuring
def darkness(px):
    """px (..., 3) sRGB 0..255 -> (d_srgb, d_lin) averaged over channels"""
    Y = (srgb_to_lin(px) * np.array([0.2126, 0.7152, 0.0722])).sum(-1)  # luminance: the owner's
    # panel resamples the 2x frame, so subpixels are not seen as subpixels
    Ys = np.where(Y <= 0.0031308, 12.92 * Y, 1.055 * Y ** (1 / 2.4) - 0.055)
    return 1 - Ys, 1 - Y


def glyph_canvas(font, ch, whole, key, v, pad=4):
    r = render_glyph(font, ch, key, v.mode, v.flags, v.emb)
    if r is None:
        return None
    a, l, t = r
    return a, whole + l, t


def compose(font, text, v, H=None, base=None, margin=3):
    pl = v.place(font, text)
    asc = int(np.ceil(font.face.size.ascender / 64.0)) + 1
    desc = int(np.ceil(-font.face.size.descender / 64.0)) + 1
    H = H or asc + desc
    base = base or asc
    W = sum(font.metrics(c)[1] for c in text) + 2 * margin + 2
    cv = np.zeros((H, W, 3) if v.mode == 'rgb' else (H, W))
    for (whole, key), c in zip(pl, text):
        g = glyph_canvas(font, c, whole, key, v)
        if g is None:
            continue
        a, x0, t = g
        y0 = base - t; x0 += margin
        ys, xs = max(0, -y0), max(0, -x0)
        sl = cv[y0 + ys:y0 + a.shape[0], x0 + xs:x0 + a.shape[1]]
        np.maximum(sl, a[ys:ys + sl.shape[0], xs:xs + sl.shape[1]], out=sl)
    return to_pixels(cv, v.mode, v.gamma), pl, base, margin


def measure_word(font, text, v, stats):
    pl = v.place(font, text)
    ideal = ideal_positions(font, text)
    # --- stems, 1x and as seen, glyph by glyph
    for (whole, key), c in zip(pl, text):
        st = glyph_stems(font, c)
        if not st:
            continue
        g = glyph_canvas(font, c, whole, key, v)
        if g is None:
            continue
        a, gx, top = g
        px = to_pixels(a if v.mode == 'rgb' else a, v.mode, v.gamma)
        ds, dl = darkness(px)
        smap = stem_map(font, c, key)
        spread = 0.5 + (2 / 3.0 if v.mode == "rgb" else 0.0)
        for L, R, (dtop, rows), wgt in st:
            Lp, Rp = whole + smap(L) - spread, whole + smap(R) + spread
            cols = [x for x in range(px.shape[1]) if Lp - 1e-6 <= gx + x + 0.5 <= Rp + 1e-6]
            rr = [r + (top - dtop) for r in rows if 0 <= r + (top - dtop) < px.shape[0]]
            if not cols or not rr:
                continue
            ink = np.median([dl[r, cols].sum() for r in rr])
            peak = np.median([ds[r, cols].max() for r in rr])
            stats['ink'].append(ink); stats['peak'].append(peak)
            # as seen: the glyph image at every horizontal sampling phase of
            # the owner's panel; ups: 2 = exact 2x blocks (scaling=exact),
            # 'halftone' = Wine's halftone 2x (scaling=smooth), 1 = native 2x
            ups = [1] if getattr(v, 'k', 2) == 1 else [2, 'halftone']
            for up in ups:
                kk = 1 if up == 1 else 2
                key_i, key_p = ('s_ink', 's_peak') if up != 'halftone' else ('h_ink', 'h_peak')
                for xo in range(8 // kk):
                    big = np.full((px.shape[0] + 2, px.shape[1] + 8, 3), 255.0)
                    big[1:1 + px.shape[0], 4:4 + px.shape[1]] = px
                    off = (gx + xo) % (8 // kk)
                    seen = as_seen(big, 1.6, off, 0, up)
                    sds, sdl = darkness(seen)
                    # panel col j samples frame col u_j = 1.6 (j + .5) - .5
                    u = 1.6 * (np.arange(seen.shape[1]) + 0.5) - 0.5
                    x1 = (u + 0.5) / kk - off - 4  # continuous 1x (or 2x) coordinate in px
                    supp = 0.5 / kk + (0.5 if up == 'halftone' else 0.0)
                    jx = [j for j in range(seen.shape[1]) if cols[0] - supp <= x1[j] <= cols[-1] + 1 + supp]
                    v2 = 1.6 * (np.arange(seen.shape[0]) + 0.5) - 0.5
                    y1 = (v2 + 0.5) / kk - 1
                    ri = [i for i in range(seen.shape[0]) if int(np.floor(y1[i] - 0.5)) in rr and
                          int(np.floor(y1[i] + 0.5)) in rr]
                    if not jx or not ri:
                        continue
                    stats[key_i].append(np.median([sdl[i, jx].sum() for i in ri]) * 0.8)
                    stats[key_p].append(np.median([sds[i, jx].max() for i in ri]))
    # --- spacing: coverage centroids vs the ideal outline at the exact position
    errs = []
    for (whole, key), c, p in zip(pl, text, ideal):
        r = render_glyph(font, c, key, v.mode, v.flags, v.emb)
        ref = render_glyph(font, c, ('shift', 0), 'gray', LOAD_LIGHT, 0)
        if r is None or ref is None:
            errs.append(None); continue
        a, l, t = r
        cov = a.mean(2) if v.mode == 'rgb' else a
        prof = cov.sum(0)
        cx = whole + l + (prof * (np.arange(len(prof)) + 0.5)).sum() / prof.sum()
        ra, rl, rt = ref
        rp = ra.sum(0)
        rcx = p + rl + (rp * (np.arange(len(rp)) + 0.5)).sum() / rp.sum()
        if v.mode == 'rgb':
            cx -= 0.0  # FreeType's LCD bitmap is centred on the outline (5-tap filter is symmetric)
        if v.emb:
            pass
        errs.append(cx - rcx)
    for i in range(1, len(errs)):
        if errs[i] is not None and errs[i - 1] is not None:
            stats['gap'].append(errs[i] - errs[i - 1])
    # --- run width (ink extent) vs ideal ink extent
    img, _, _, margin = compose(font, text, v)
    ds, dl = darkness(img)
    colink = dl.sum(0)
    xs = np.nonzero(colink > 0.05)[0]
    if len(xs):
        first = xs[0] - margin
        last = xs[-1] + 1 - margin
        # ideal ink extent
        f0 = render_glyph(font, text[0], ('shift', 0), 'gray', LOAD_LIGHT, 0)
        f1 = render_glyph(font, text[-1], ('shift', 0), 'gray', LOAD_LIGHT, 0)
        ilo = ideal[0] + f0[1]
        ihi = ideal[-1] + f1[1] + f1[0].shape[1]
        stats['width'].append((last - first) - (ihi - ilo))


def run(variants, sizes=(10, 11), styles=('regular', 'bold'), words=WORDS):
    rows = []
    for v in variants:
        for style in styles:
            for size in sizes:
                font = FONTS[(style, size)]
                st = {k: [] for k in ('ink', 'peak', 's_ink', 's_peak', 'h_ink', 'h_peak', 'gap', 'width')}
                st['wgap'] = []
                for w in words:
                    measure_word(font, w, v, st)
                    st['wgap'] += white_gaps(font, w, v)
                rows.append(summ(v, style, size, st))
    return rows


def cv(x):
    x = np.asarray(x); return float(x.std() / x.mean()) if len(x) else float('nan')


def summ(v, style, size, st):
    gap = np.asarray(st['gap'])
    return dict(variant=v.name, mode=v.mode, style=style, size=size, n=len(st['peak']),
                peak_mean=float(np.mean(st['peak'])), peak_cv=cv(st['peak']),
                peak_rng=float(np.ptp(st['peak'])),
                ink_mean=float(np.mean(st['ink'])), ink_cv=cv(st['ink']), ink_rng=float(np.ptp(st['ink'])),
                s_peak_cv=cv(st['s_peak']), s_ink_cv=cv(st['s_ink']), s_ink_mean=float(np.mean(st['s_ink'])),
                h_peak_cv=cv(st['h_peak']), h_ink_cv=cv(st['h_ink']),
                gap_rms=float(np.sqrt((gap ** 2).mean())), gap_max=float(np.abs(gap).max()),
                wgap_rms=float(np.sqrt(np.mean(np.square(st['wgap'])))), wgap_max=float(np.max(np.abs(st['wgap']))),
                wgap_bias=float(np.mean(st['wgap'])),
                width_mae=float(np.mean(np.abs(st['width']))))


FONTS = {(s, p): Font(REG if s == 'regular' else BOLD, p) for s in ('regular', 'bold') for p in (10, 11, 13, 16, 20, 22)}


# ---------------- stem snapping with a spacing-aware choice of rounding ---
def snap_moves(font, ch, s64, bias, minw=1.0, grid=1.0, maxmove=0.75, alpha=1.0):  # noqa
    """per stem (old L, old R, new L, new R) when every stem of ch (placed at
    local shift s64) is snapped with floor(x + 0.5 + bias); None if a stem
    would move more than maxmove px or stems would collide"""
    out = []
    for L, R, rows, w in glyph_stems(font, ch):
        Lp, Rp = L + s64 / 64.0, R + s64 / 64.0
        W = max(minw, round((R - L) / grid) * grid)
        c = (Lp + Rp) / 2
        nL = np.floor((c - W / 2) / grid + 0.5 + bias) * grid
        if abs(nL + W / 2 - c) > maxmove:
            return None
        if alpha != 1.0:  # partial snap: centre and width move a fraction of the way
            cf = nL + W / 2
            W = (R - L) + alpha * (W - (R - L))
            nL = c + alpha * (cf - c) - W / 2
        out.append((Lp, Rp, nL, nL + W, w))
    out.sort()
    for a, b in zip(out, out[1:]):
        if b[2] < a[3] + 0.99 * alpha or b[0] <= a[1]:
            return None
    return out


def xmap_snapb(font, ch, s64, bias, alpha=1.0):
    mv = snap_moves(font, ch, s64, bias, alpha=alpha)
    knots = []
    for Lp, Rp, nL, nR, w in mv or []:
        knots += [(Lp, nL), (Rp, nR)]

    def f(xs):
        x = xs / 64.0 + s64 / 64.0
        if not knots:
            return x * 64
        o = np.array([k[0] for k in knots]); nw = np.array([k[1] for k in knots])
        y = np.interp(x, o, nw)
        y = np.where(x < o[0], x + (nw[0] - o[0]), y)
        y = np.where(x > o[-1], x + (nw[-1] - o[-1]), y)
        return y * 64
    return f


XMAPS['snapb'] = xmap_snapb


class StemSnapDP(Variant):
    """stems snapped to whole pixels (crisp); per glyph the rounding is
    nearest, down or up (a stem moves at most 0.75 px), glyphs without stems
    may move by a third; a Viterbi pass over the run picks the choices that
    keep the displacement of neighbours alike (even gaps) and small"""
    lam = 0.15   # weight of the absolute displacement
    biases = (-0.5, 0.0, 0.5)
    sh = (-1, 0, 1)  # thirds for stemless glyphs
    ends = 0.5   # first/last glyph: max |displacement|

    def options(self, font, c, whole, s64):
        st = glyph_stems(font, c)
        opts = []
        if st:
            for b in self.biases:
                mv = snap_moves(font, c, s64, b)
                if mv is None:
                    continue
                wsum = sum(m[4] for m in mv)
                e = sum(((m[2] + m[3]) / 2 - (m[0] + m[1]) / 2) * m[4] for m in mv) / wsum
                opts.append((e, (whole, ('snapb', s64, b))))
        if not opts:
            q = whole * 3 + (s64 * 3 + 32) // 64
            for d in self.sh:
                qq = q + d
                opts.append((d / 3.0, (qq // 3, ('shift', ((qq % 3) * 64 + 1) // 3))))
        return opts

    def place(self, font, text):
        base = thirds_place(font, text, 3)
        cands = [self.options(font, c, w, s) for (w, s), c in zip(base, text)]
        n = len(text)
        INF = 1e9

        def unary(i, e):
            if (i == 0 or i == n - 1) and abs(e) > self.ends + 1e-9:
                return INF
            return self.lam * e * e
        best = [[unary(0, o[0]) for o in cands[0]]]
        back = []
        for i in range(1, n):
            row, bk = [], []
            for o in cands[i]:
                vals = [best[-1][j] + (o[0] - p[0]) ** 2 for j, p in enumerate(cands[i - 1])]
                j = int(np.argmin(vals))
                row.append(vals[j] + unary(i, o[0])); bk.append(j)
            best.append(row); back.append(bk)
        j = int(np.argmin(best[-1]))
        path = [j]
        for i in range(n - 2, -1, -1):
            j = back[i][j]; path.append(j)
        path.reverse()
        return [cands[i][path[i]][1] for i in range(n)]


# ---------------- white gaps between neighbouring letters ------------------
def _edges(cov, left, top, z=1):
    """per row y (absolute, baseline-relative: y = top - row): (left edge,
    right edge) of ink in px, partial coverage counted as a fraction"""
    out = {}
    for r in range(cov.shape[0]):
        row = cov[r]
        nz = np.nonzero(row > 0.1)[0]
        if not len(nz):
            continue
        a, b = nz[0], nz[-1]
        le = (left + a + 1 - row[a]) / z
        re = (left + b + row[b]) / z
        out[top - r] = (le, re)
    return out


@functools.lru_cache(maxsize=None)
def ideal_edges(font, ch, frac64):
    """same estimator on the unwarped outline at the exact (1/64 px) position"""
    r = render_glyph(font, ch, ('shift', frac64), 'gray', LOAD_LIGHT, 0)
    if r is None:
        return {}
    a, l, t = r
    return _edges(a, l, t)


def white_gaps(font, text, v):
    pl = v.place(font, text)
    ideal = ideal_positions(font, text)
    xh = int(round(0.545 * font.ppem))
    errs = []
    prev = prev_i = None
    for (whole, key), c, p in zip(pl, text, ideal):
        r = render_glyph(font, c, key, 'gray', v.flags, v.emb)
        if r is None:
            prev = None; continue
        a, l, t = r
        e = _edges(a, whole + l, t)
        fl = int(np.floor(p)); f64 = int(round((p - fl) * 64))
        ie = {y: (le + fl, re + fl) for y, (le, re) in ideal_edges(font, c, f64).items()}
        if prev is not None:
            pe, pie = prev
            ys = [y for y in range(1, xh + 1) if y in pe and y in e and y in pie and y in ie]
            if len(ys) >= 3:
                g = np.mean([e[y][0] - pe[y][1] for y in ys])
                gi = np.mean([ie[y][0] - pie[y][1] for y in ys])
                errs.append(g - gi)
        prev = (e, ie)
    return errs


class StemSnapDP2(StemSnapDP):
    """as StemSnapDP, but the Viterbi cost is the error of the white gap
    between neighbours: (left-edge displacement of glyph i - right-edge
    displacement of glyph i-1)^2, displacements measured from the exact
    ideal position (so the 1/3 px quantisation is compensated too)"""
    lam = 0.05
    sh = (-1, 0, 1)
    stem_sh = (0,)  # extra thirds tried for glyphs with stems

    def options2(self, font, c, whole, s64, ideal):
        st = glyph_stems(font, c)
        opts = []
        q = whole * 3 + (s64 * 3 + 32) // 64
        if st:
            for d in self.stem_sh:
                qq = q + d
                w2, s2 = qq // 3, ((qq % 3) * 64 + 1) // 3
                base = w2 + s2 / 64.0 - ideal
                for b in self.biases:
                    a = getattr(self, 'alpha', 1.0)
                    mv = snap_moves(font, c, s2, b, alpha=a)
                    if mv is None:
                        continue
                    dl = base + mv[0][2] - mv[0][0]
                    dr = base + mv[-1][3] - mv[-1][1]
                    opts.append((dl, dr, (w2, ('snapb', s2, b, a))))
        if not opts:
            for d in self.sh:
                qq = q + d
                w2, s2 = qq // 3, ((qq % 3) * 64 + 1) // 3
                e = w2 + s2 / 64.0 - ideal
                opts.append((e, e, (w2, ('shift', s2))))
        return opts

    def place(self, font, text):
        base = thirds_place(font, text, 3)
        ideal = ideal_positions(font, text)
        cands = [self.options2(font, c, w, s, p) for (w, s), c, p in zip(base, text, ideal)]
        n = len(text)
        INF = 1e9

        def unary(i, o):
            m = (o[0] + o[1]) / 2
            if (i == 0 or i == n - 1) and max(abs(o[0]), abs(o[1])) > self.ends + 1e-9:
                return INF
            return self.lam * m * m
        best = [[unary(0, o) for o in cands[0]]]
        back = []
        for i in range(1, n):
            row, bk = [], []
            for o in cands[i]:
                vals = [best[-1][j] + (o[0] - p[1]) ** 2 for j, p in enumerate(cands[i - 1])]
                j = int(np.argmin(vals))
                row.append(vals[j] + unary(i, o)); bk.append(j)
            best.append(row); back.append(bk)
        j = int(np.argmin(best[-1]))
        path = [j]
        for i in range(n - 2, -1, -1):
            j = back[i][j]; path.append(j)
        path.reverse()
        return [cands[i][path[i]][2] for i in range(n)]


# ---------------- the proposed C change, bit-exact model (cmodel.py) -------
import cmodel
XMAPS['cwarp'] = cmodel.xmap_cwarp


class CWarp(Variant):
    """stem-fix.diff: soft stem snap (alpha/256) + phase Viterbi"""
    alpha = 128

    def place(self, font, text):
        kw = getattr(self, 'keepw', True)
        return [(w, ('cwarp', s, self.alpha, kw)) for w, s in cmodel.place(font, text, self.alpha, getattr(self, 'ends', 32), getattr(self, 'wgap', 20), kw)]
