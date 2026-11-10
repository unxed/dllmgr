"""alpha sweep of the C model with the straight-stem detector, ends=32; metric stems: straight"""
import sys, measure, cmodel, straight
from measure import *
measure.glyph_stems = lambda font, ch, all_stems=False: straight.straight_stems(font, ch)
cmodel.glyph_stems = lambda font, ch, all_stems=False: straight.straight_stems(font, ch)
sizes = tuple(int(x) for x in sys.argv[2].split(',')) if len(sys.argv) > 2 else (10, 11)
for mode in sys.argv[1].split(','):
    for a in (0, 64, 96, 128, 160, 192, 256):
        v = Variant('agg', mode) if a == 0 else CWarp('x', mode, alpha=a, ends=32)
        if len(sys.argv) > 3: v.k = 1
        rs = run([v], sizes=sizes, styles=('regular',)); m = lambda k: float(np.mean([r[k] for r in rs]))
        print(f"{sizes} {mode} alpha {a:3} peak {m('peak_mean'):.2f} cv {m('peak_cv'):.3f} seen {m('s_peak_cv'):.3f} smooth {m('h_peak_cv'):.3f} | ink cv {m('ink_cv'):.3f} | white {m('wgap_rms'):.3f} | centroid {m('gap_rms'):.3f}/{max(r['gap_max'] for r in rs):.2f} | w {m('width_mae'):.2f}", flush=True)
