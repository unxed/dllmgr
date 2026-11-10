"""final numbers: current agg, rejected snap, stem fix (stem-fix.diff), regular 10/11 (+13/16 check)"""
import json, sys
from measure import *
def V(mode):
    a = 128 if mode == 'rgb' else 192
    return [Variant('agg (current)', mode), Snap('x-snap + full hint (rejected)', mode, flags=LOAD_NORMAL),
            CWarp(f'stem fix (alpha {a}/256)', mode, alpha=a, ends=0)]
sizes = tuple(int(x) for x in sys.argv[1].split(',')) if len(sys.argv) > 1 else (10, 11)
styles = tuple(sys.argv[2].split(',')) if len(sys.argv) > 2 else ('regular',)
rows = []
for mode in ('rgb', 'gray'):
    for v in V(mode):
        rs = run([v], sizes=sizes, styles=styles)
        m = lambda k: float(np.mean([r[k] for r in rs]))
        row = dict(variant=v.name, mode=mode, n=sum(r['n'] for r in rs), peak=m('peak_mean'), peak_cv=m('peak_cv'),
                   seen_peak_cv=m('s_peak_cv'), smooth_peak_cv=m('h_peak_cv'), ink_cv=m('ink_cv'),
                   seen_ink_cv=m('s_ink_cv'), gap=m('gap_rms'), gap_max=max(r['gap_max'] for r in rs),
                   white=m('wgap_rms'), width=m('width_mae'))
        rows.append(row)
        print(f"| {mode} | {v.name} | {row['peak']:.2f} | {row['peak_cv']:.3f} | {row['seen_peak_cv']:.3f} | {row['smooth_peak_cv']:.3f} | {row['ink_cv']:.3f} | {row['seen_ink_cv']:.3f} | {row['gap']:.3f} / {row['gap_max']:.2f} | {row['white']:.3f} | {row['width']:.2f} |", flush=True)
json.dump(rows, open(f"final-{'-'.join(map(str,sizes))}-{'-'.join(styles)}.json", 'w'), indent=1)
