"""C helpers (stem-fix.diff, built standalone in ctest/harness) vs cmodel.py"""
import subprocess, sys, numpy as np
from measure import WORDS, FONTS, LOAD_LIGHT
import cmodel
from ftlab import REG, BOLD
bad = tot = 0
for style, path in (('regular', REG), ('bold', BOLD)):
    for ppem in (10, 11):
        f = FONTS[(style, ppem)]
        chars = sorted(set(''.join(WORDS)))
        for alpha in (128, 192):
            out = subprocess.run(['ctest/harness', path, str(ppem), str(alpha)] + [str(ord(c)) for c in chars],
                                 capture_output=True, text=True, check=True).stdout.split('\n')
            for line in filter(None, out):
                cp, ph, rest = line.split(' ', 2)
                k, x = rest.split(' X')
                ck = [tuple(map(int, t.split(','))) for t in k[1:].split()]
                cx = list(map(int, x.split()))
                c = chr(int(cp)); s = (int(ph) * 64 + 1) // 3
                pk = [p for pair in cmodel.knots(f, c, s, alpha) for p in [pair]]
                xs, ys, tags, conts = f.load_points(c, LOAD_LIGHT)
                px = list(cmodel.warp_x(np.asarray(xs, np.int64) + s, cmodel.knots(f, c, s, alpha)))
                tot += 1
                if [tuple(p) for p in pk] != ck or [int(v) for v in px] != cx:
                    bad += 1
                    if bad < 6: print('MISMATCH', style, ppem, alpha, c, ph, ck, pk)
print(f'{tot - bad}/{tot} glyph renders identical (knots and every warped point)')
