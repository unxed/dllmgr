#!/usr/bin/env python3
"""#66: which bitmap-shear rule turns Windows' upright Tahoma glyphs into
Windows' simulated italic ones? stitch.py WINDOWS-bits66.txt"""
import sys, math
def load(p):
    g = {}
    for line in open(p):
        f = line.rstrip('\n').split(' ')
        if len(f) < 6: continue
        g[(f[0], int(f[1]), int(f[2]))] = (int(f[3]), int(f[4]), f[5].split('/') if f[5] else [])
    return g
def grid(v):
    ox, oy, rows = v
    return {(ox + i, oy - 1 - r) for r, row in enumerate(rows) for i, c in enumerate(row) if c == '#'}
def rnd(v): return int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)
shift = lambda y: rnd((y + 0.5) / 3)
def italic(up, rule):
    out = {(x + shift(y), y) for x, y in up}
    if rule == 'shift': return out
    for x, y in up:
        if shift(y) == shift(y - 1): continue
        below = [(x + d, y - 1) for d in ((0,) if rule.endswith('v') else (-1, 0, 1))]
        if any(b in up for b in below):
            if rule.startswith('up'): out.add((x + shift(y) - 1, y))
            else: out.add((x + shift(y - 1) + 1, y - 1))
    return out
G = load(sys.argv[1])
for rule in ('shift', 'up-v', 'down-v', 'up-any', 'down-any'):
    res = []
    for size in range(9, 17):
        same = sum(1 for ch in range(0x21, 0x7f) if ('regular', size, ch) in G and ('italic', size, ch) in G and
                   italic(grid(G[('regular', size, ch)]), rule) == grid(G[('italic', size, ch)]))
        res.append(same)
    print(rule, res)
