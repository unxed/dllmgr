from table1 import fmt
from measure import *
vs=[Variant('agg (current)'), Variant('sixths',step=6), Snap('snap (rejected)',flags=LOAD_NORMAL), StemSnap('stemsnap'), StemSnapDP('stemsnap-dp')]
for v in vs:
    for r in run([v], styles=('regular',)): print(fmt(r), flush=True)
