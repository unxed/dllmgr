from table1 import fmt
from measure import *
vs = [Variant('agg (current)'),
      StemSnap('stemsnap tol.5'), StemSnap('stemsnap tol.34', tol=0.34), StemSnap('stemsnap tol.17', tol=0.17),
      SharpPhase('sharp r1 l.02'), SharpPhase('sharp r1 l.1', lam=0.1), SharpPhase('sharp r1 l.0 g0', lam=0.0, gap=0.0),
      Variant('sixths', step=6), Variant('agg emb.2 g1.0', gamma=1.0, emb=0.2), Variant('agg emb.3 g1.0', gamma=1.0, emb=0.3),
      Variant('agg emb.2 g1.3', gamma=1.3, emb=0.2),
      StemSnap('stemsnap tol.5 g1.0', gamma=1.0), StemSnap('stemsnap .5 emb.2 g1.0', gamma=1.0, emb=0.2),
      Variant('agg (current)', 'rgb'), StemSnap('stemsnap1/3 tol.17', 'rgb', grid=1/3, tol=0.17),
      StemSnap('stemsnap1 tol.5', 'rgb'), StemSnap('stemsnap1 tol.34', 'rgb', tol=0.34), SharpPhase('sharp r1 l.02', 'rgb')]
for v in vs:
    for r in run([v], styles=('regular',)):
        print(fmt(r), flush=True)
