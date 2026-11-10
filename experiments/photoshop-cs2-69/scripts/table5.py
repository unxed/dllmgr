from table1 import fmt
from measure import *
vs=[Variant('agg (current)'), StemSnap('stemsnap'), StemSnapDP('stemsnap-dp'), StemSnapDP('stemsnap-dp lam.05', lam=0.05), StemSnapDP('stemsnap-dp lam.5', lam=0.5),
    Variant('agg (current)','rgb'), StemSnapDP('stemsnap-dp','rgb')]
for v in vs:
    for r in run([v], styles=('regular',)): print(fmt(r), flush=True)
