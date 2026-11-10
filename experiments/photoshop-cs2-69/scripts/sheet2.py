import sys
from sheet import *
from measure import *
K = dict(biases=(0.0,), stem_sh=(-1, 0, 1))
mode = sys.argv[1]
vs = [Variant('agg (current)', mode),
      StemSnapDP2('soft snap a.5', mode, alpha=0.5, **K), StemSnapDP2('soft snap a.67', mode, alpha=0.67, **K),
      StemSnapDP2('soft snap a.75', mode, alpha=0.75, **K), StemSnapDP2('full snap a1', mode, alpha=1.0, **K),
      Snap('snap+full hint (rejected)', mode, flags=LOAD_NORMAL)]
print(sheet(vs, ['Contrast:', 'Brightness:', 'Channels'], f'sheet-{mode}.png'))
