from measure import *
res=[]
for g in (1.0,1.2,1.4,1.6):
  for e in (0.0,0.1,0.2,0.3,0.4):
    v=Variant(f'e{e} g{g}',gamma=g,emb=e)
    rs=run([v],styles=('regular',))
    a=np.mean([r['ink_mean'] for r in rs]); c=np.mean([r['ink_cv'] for r in rs]); p=np.mean([r['peak_mean'] for r in rs]); pc=np.mean([r['peak_cv'] for r in rs])
    s=np.mean([r['s_ink_cv'] for r in rs]); h=np.mean([r['h_ink_cv'] for r in rs])
    print(f'g{g} e{e}: ink {a:.2f} cv {c:.3f} | peak {p:.2f} cv {pc:.3f} | seen {s:.3f} smooth {h:.3f}',flush=True)
