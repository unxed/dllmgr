"""C-model variants by stem detector; metric stems: clean (stems.py) or straight (straight.py)"""
import sys, measure, cmodel, stems, straight
from measure import *
mode = sys.argv[1]; a = int(sys.argv[2]); metric = sys.argv[3]
if metric == 'straight':
    measure.glyph_stems = lambda font, ch, all_stems=False: straight.straight_stems(font, ch)
dets = {'all (wip C)': lambda font, ch, all_stems=False: stems.glyph_stems(font, ch, True),
        'clean': lambda font, ch, all_stems=False: stems.glyph_stems(font, ch, False),
        'straight': lambda font, ch, all_stems=False: straight.straight_stems(font, ch)}
v0 = Variant('agg', mode); rs = run([v0], styles=('regular',)); m = lambda k: float(np.mean([r[k] for r in rs]))
print(f"metric={metric} {mode} agg (current)                 peak cv {m('peak_cv'):.3f} seen {m('s_peak_cv'):.3f} | ink cv {m('ink_cv'):.3f} | white {m('wgap_rms'):.3f} | centroid {m('gap_rms'):.3f}/{max(r['gap_max'] for r in rs):.2f} | w {m('width_mae'):.2f}")
for dn, det in dets.items():
    cmodel.glyph_stems = det; cmodel.knots.cache_clear(); measure.render_glyph.cache_clear()
    for kw in [dict(ends=0), dict(ends=32)]:
        v = CWarp(dn + str(kw), mode, alpha=a, **kw); rs = run([v], styles=('regular',))
        print(f"metric={metric} {mode} {a} {dn:12} {str(kw):12} peak cv {m('peak_cv'):.3f} seen {m('s_peak_cv'):.3f} | ink cv {m('ink_cv'):.3f} | white {m('wgap_rms'):.3f} | centroid {m('gap_rms'):.3f}/{max(r['gap_max'] for r in rs):.2f} | w {m('width_mae'):.2f}", flush=True)
