from measure import *
import json
out=[]
for mode in ('rgb','gray'):
  for a in (0.0, 0.33, 0.5, 0.6, 0.67, 0.75, 0.85, 1.0):
    v = Variant('agg (current)', mode) if a == 0 else StemSnapDP2(f'dp2 a{a}', mode, alpha=a)
    rs = run([v], styles=('regular',))
    m = lambda k: np.mean([r[k] for r in rs])
    print(f"{mode} a={a:<5} peak {m('peak_mean'):.2f} cv {m('peak_cv'):.3f} seen-pk-cv {m('s_peak_cv'):.3f} | ink cv {m('ink_cv'):.3f} seen {m('s_ink_cv'):.3f} | white {m('wgap_rms'):.3f} max {m('wgap_max'):.2f} | gap {m('gap_rms'):.3f}", flush=True)
    out.append(dict(mode=mode, alpha=a, **{k: m(k) for k in rs[0] if isinstance(rs[0][k], float)}))
json.dump(out, open('pareto.json','w'), indent=1)
