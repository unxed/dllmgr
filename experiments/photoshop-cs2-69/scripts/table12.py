from measure import *
for mode in ('rgb',):
  for kw in [dict(alpha=128), dict(alpha=128, ends=21), dict(alpha=128, wgap=5), dict(alpha=128, wgap=80), dict(alpha=160), dict(alpha=160, ends=21), dict(alpha=96)]:
    v=CWarp(str(kw), mode, **kw); rs=run([v], styles=('regular',))
    m=lambda k: np.mean([r[k] for r in rs])
    print(f"{str(kw):32} peak cv {m('peak_cv'):.3f} seen {m('s_peak_cv'):.3f} smooth {m('h_peak_cv'):.3f} | centroid gap {m('gap_rms'):.3f}/{m('gap_max'):.2f} white {m('wgap_rms'):.3f} | w {m('width_mae'):.2f}", flush=True)
