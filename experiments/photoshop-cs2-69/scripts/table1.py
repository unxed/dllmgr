import sys, time, json
from measure import *
def fmt(r):
    return (f"{r['variant']:<26}{r['mode']:<5}{r['style'][:3]:<4}{r['size']:>3}{r['n']:>5} "
            f"pk {r['peak_mean']:.2f} cv {r['peak_cv']:.3f} | ink {r['ink_mean']:.2f} cv {r['ink_cv']:.3f} rng {r['ink_rng']:.2f} | "
            f"seen pk {r['s_peak_cv']:.3f} ink {r['s_ink_cv']:.3f} | smooth pk {r['h_peak_cv']:.3f} ink {r['h_ink_cv']:.3f} | gap {r['gap_rms']:.3f}/{r['gap_max']:.2f} white {r['wgap_rms']:.3f}/{r['wgap_max']:.2f} b{r['wgap_bias']:+.2f} | w {r['width_mae']:.2f}")
if __name__ == '__main__':
    vs = [Variant('agg (current)'), Variant('agg g1.0', gamma=1.0), Variant('agg g1.6', gamma=1.6),
          Snap('snap+normal hint', flags=LOAD_NORMAL),
          Variant('agg (current)', 'rgb'), Snap('snap+normal hint', 'rgb', flags=LOAD_NORMAL)]
    t=time.time()
    for v in vs:
        for r in run([v], styles=('regular',)):
            print(fmt(r), flush=True)
    print(time.time()-t)
