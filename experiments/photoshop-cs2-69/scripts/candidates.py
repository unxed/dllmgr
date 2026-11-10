"""#69: every candidate approach on the same words (measure.WORDS), Tahoma
regular 10/11 px (Photoshop CS2 dialogs/palettes), agg-rgb and agg (grey).
Metrics (mean over the two sizes):
  peak cv   : CV of stem peak darkness (sRGB), 1x               lower = even
  seen      : same after the owner's panel (2x exact blocks, 1/1.6 bilinear)
  smooth    : same with Wine's halftone 2x (scaling=smooth)
  ink cv    : CV of stem ink (linear light), 1x
  white     : RMS error of the white gap between neighbours vs the exact
              outline at the exact fractional position, px
  centroid  : RMS / max error of neighbour distance (coverage centroids), px
  width     : mean |run ink extent - ideal|, px"""
import sys, json, numpy as np
import measure
from measure import *

_orig_render = measure.render_glyph

@functools.lru_cache(maxsize=200000)
def render_dark(font, ch, key, mode, flags, emb):
    if key[0] != 'dark':
        return _orig_render(font, ch, key, mode, flags, emb)
    s64, k = key[1], key[2]
    r = _orig_render(font, ch, ('shift', s64), mode, flags, emb)
    if r is None: return None
    st = glyph_stems(font, ch)
    if not st: return r
    split = np.mean([min((L + s64 / 64) % 1, 1 - (L + s64 / 64) % 1) for L, R, rows, w in st])
    a, l, t = r
    return 1 - (1 - a) ** (1 + k * 2 * split), l, t
measure.render_glyph = render_dark
XMAPS['dark'] = lambda font, ch, s64, k: (lambda xs: xs + s64)

class PhaseDark(Variant):
    """phase-dependent stem darkening: a glyph whose stems straddle pixels
    gets its coverage boosted (1 - (1 - c)^(1 + k * 2 * split)), split =
    mean distance of its stems' left edges from the pixel grid (0..0.5)"""
    k = 1.0
    def place(self, font, text):
        return [(w, ('dark', s, self.k)) for w, s in thirds_place(font, text, 3)]

def cands(mode):
    a = 128 if mode == 'rgb' else 192
    K = dict(biases=(0.0,), stem_sh=(-1, 0, 1))
    return [
        ('A', 'agg (current): 1/3 px phases, vertical-only hinting', Variant('agg', mode)),
        ('B', 'whole-px positions + full hinting (classic, rejected in #69)', Snap('snap', mode, flags=LOAD_NORMAL)),
        ('C', 'finer phases: 1/6 px', Variant('sixths', mode, step=6)),
        ('D1', 'global darkening: embolden 0.2 px, gamma 1.4', Variant('emb', mode, gamma=1.4, emb=0.2) if mode == 'gray' else Variant('emb', mode, emb=0.2)),
        ('D2', 'phase-dependent darkening k=1', PhaseDark('pd1', mode, k=1.0)),
        ('D3', 'phase-dependent darkening k=2', PhaseDark('pd2', mode, k=2.0)),
        ('E', 'per-glyph phase for sharpest bitmap (Viterbi, +-1/3 px)', SharpPhase('sharp', mode)),
        ('F1', 'hard stem snap to whole px (outline warp), advance fractional', StemSnap('snap1', mode)),
        ('F2', 'hard stem snap to 1/3 px grid (rgb only meaningful)', StemSnap('snap13', mode, grid=1/3, tol=0.17)),
        ('G', 'hard stem snap + rounding/phase by Viterbi on white gaps', StemSnapDP2('dp2', mode, alpha=1.0, **K)),
        ('H', 'soft stem snap a=0.5 + Viterbi (float model)', StemSnapDP2('dp2', mode, alpha=0.5, **K)),
        ('I', f'chosen: soft snap {a}/256 + phase Viterbi (C, stem-fix.diff)', CWarp('fix', mode, alpha=a, ends=0)),
    ]

if __name__ == '__main__':
    sizes = tuple(int(x) for x in sys.argv[1].split(',')) if len(sys.argv) > 1 else (10, 11)
    out = []
    print(f'sizes {sizes}, Tahoma regular')
    print('| mode | id | candidate | peak cv | seen | smooth | ink cv | white rms | centroid rms / max | width |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for mode in ('rgb', 'gray'):
        for cid, name, v in cands(mode):
            if len(sys.argv) > 2: v.k = 1  # native 2x text (#52b GDI scaling): no 2x upscale in the panel model
            rs = run([v], sizes=sizes, styles=('regular',))
            m = lambda k: float(np.mean([r[k] for r in rs]))
            row = dict(mode=mode, id=cid, name=name, **{k: m(k) for k in rs[0] if isinstance(rs[0][k], float)})
            row['gap_max'] = max(r['gap_max'] for r in rs)
            out.append(row)
            print(f"| {mode} | {cid} | {name} | {row['peak_cv']:.3f} | {row['s_peak_cv']:.3f} | {row['h_peak_cv']:.3f} | {row['ink_cv']:.3f} | {row['wgap_rms']:.3f} | {row['gap_rms']:.3f} / {row['gap_max']:.2f} | {row['width_mae']:.2f} |", flush=True)
    json.dump(out, open(f"candidates-{'-'.join(map(str, sizes))}.json", 'w'), indent=1)
