from table1 import fmt
from measure import *
import sys
vs = [Variant('agg (current)'),
      StemSnap('stemsnap'), SharpPhase('sharp-phase'), Variant('sixths', step=6),
      Variant('agg emb.2 g1.0', gamma=1.0, emb=0.2), Variant('agg emb.25 g1.2', gamma=1.2, emb=0.25),
      Variant('agg emb.3 g1.0', gamma=1.0, emb=0.3), Variant('agg emb.15 g1.4', gamma=1.4, emb=0.15),
      Variant('agg (current)', 'rgb'), StemSnap('stemsnap', 'rgb'), StemSnap('stemsnap1/3', 'rgb', grid=1/3, tol=0.17),
      Variant('sixths', 'rgb', step=6), Variant('agg emb.2', 'rgb', emb=0.2)]
for v in vs:
    for r in run([v], styles=('regular',)):
        print(fmt(r), flush=True)
