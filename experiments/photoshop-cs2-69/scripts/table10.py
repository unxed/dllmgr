from measure import *
for mode in ('rgb','gray'):
  for a in (0.5, 0.6, 0.67, 0.75, 1.0):
    for name, kw in [('dp-shift', dict(biases=(0.0,))), ('dp-shift-all', dict(biases=(0.0,), stem_sh=(-1,0,1)))]:
        v = StemSnapDP2(f'{name} a{a}', mode, alpha=a, **kw)
        rs = run([v], styles=('regular',))
        m = lambda k: np.mean([r[k] for r in rs])
        print(f"{mode} a={a:<5}{name:13} peak cv {m('peak_cv'):.3f} seen-pk {m('s_peak_cv'):.3f} | white {m('wgap_rms'):.3f} max {m('wgap_max'):.2f} | gap {m('gap_rms'):.3f}", flush=True)
