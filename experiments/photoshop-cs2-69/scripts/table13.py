from measure import *
for mode,alphas in (('rgb',(128,)),('gray',(128,192))):
  for a in alphas:
   for kw in [dict(alpha=a), dict(alpha=a, ends=0)]:
    v=CWarp(str(kw), mode, **kw); rs=run([v])
    for r in rs: print(f"{mode} {str(kw):24}{r['style'][:3]} {r['size']} peak cv {r['peak_cv']:.3f} seen {r['s_peak_cv']:.3f} smooth {r['h_peak_cv']:.3f} | centroid gap {r['gap_rms']:.3f}/{r['gap_max']:.2f} white {r['wgap_rms']:.3f} | w {r['width_mae']:.2f}", flush=True)
