from table1 import fmt
from measure import *
vs=[StemSnapDP2('dp2 a.5', alpha=0.5), StemSnapDP2('dp2 a.75', alpha=0.75), StemSnapDP2('dp2 a.5','rgb', alpha=0.5),StemSnapDP2('dp2 a1','rgb')]
for v in vs:
    for r in run([v], styles=('regular',)): print(fmt(r), flush=True)
