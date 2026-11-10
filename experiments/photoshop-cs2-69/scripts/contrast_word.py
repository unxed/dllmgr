"""'Contrast:' stem by stem (Tahoma regular, Photoshop placement): peak darkness / ink"""
from measure import *
import phase_table  # straight stems
from phase_table import stem_vals
for size in (10, 11):
    f = FONTS[('regular', size)]
    for mode, alpha in (('rgb', 128), ('gray', 128)):
        for name, v in (('agg', Variant('agg', mode)), ('fix', CWarp('fix', mode, alpha=alpha, ends=32))):
            pl = v.place(f, 'Contrast:'); cells = []; pks = []
            for (whole, key), c in zip(pl, 'Contrast:'):
                for Lp, w, pk, ink in stem_vals(f, c, key, v):
                    cells.append(f'{c}@{(whole + Lp) % 1:.2f}:{pk:.2f}'); pks.append(pk)
            print(f'{size} {mode} {name:4} min {min(pks):.2f} max {max(pks):.2f} | ' + '  '.join(cells))
