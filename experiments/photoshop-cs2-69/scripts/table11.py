from table1 import fmt
from measure import *
vs=[Variant('agg (current)'), CWarp('C model a.75 (192)', alpha=192), CWarp('C model a.5 (128)', alpha=128),
    Variant('agg (current)','rgb'), CWarp('C model a.5 (128)','rgb', alpha=128), CWarp('C model a.75 (192)','rgb', alpha=192)]
for v in vs:
    for r in run([v]): print(fmt(r), flush=True)
