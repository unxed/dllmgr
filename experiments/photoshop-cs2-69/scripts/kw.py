from measure import *
for sizes in ((10,11),(13,16)):
  for mode,a in (('rgb',128),('gray',192),('gray',128)):
    for kw in (False, True):
        v=CWarp('x',mode,alpha=a,ends=0,keepw=kw); rs=run([v],sizes=sizes,styles=('regular',))
        m=lambda k: float(np.mean([r[k] for r in rs]))
        print(sizes,mode,a,'keepw' if kw else 'roundw',f"peak cv {m('peak_cv'):.3f} seen {m('s_peak_cv'):.3f} | ink cv {m('ink_cv'):.3f} seen {m('s_ink_cv'):.3f} | gap {m('gap_rms'):.3f} white {m('wgap_rms'):.3f}",flush=True)
