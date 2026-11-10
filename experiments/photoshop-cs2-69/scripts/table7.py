from table1 import fmt
from measure import *
vs=[StemSnapDP2('stemsnap-dp2'), StemSnapDP2('stemsnap-dp2 lam.01', lam=0.01), StemSnapDP2('stemsnap-dp2 lam.2', lam=0.2),
    StemSnapDP2('stemsnap-dp2 sh2', sh=(-2,-1,0,1,2)), StemSnapDP2('stemsnap-dp2 ends.75', ends=0.75)]
for v in vs:
    for r in run([v], styles=('regular',)): print(fmt(r), flush=True)
