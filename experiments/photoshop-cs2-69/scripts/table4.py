from table1 import fmt
from measure import *
vs=[StemSnap('stemsnap half', goff=0.5), StemSnap('stemsnap half g1', goff=0.5, gamma=1.0), StemSnap('stemsnap half', 'rgb', goff=0.5)]
for v in vs:
    for r in run([v], styles=('regular',)): print(fmt(r), flush=True)
