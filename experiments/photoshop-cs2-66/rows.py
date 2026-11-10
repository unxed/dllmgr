#!/usr/bin/env python3
"""#66 italic rows: for each glyph, row by row, how far the italic row is
shifted against the same row of the upright glyph (both monochrome GDI
bitmaps from text-metrics66 bits66.txt). rows.py BITS.txt"""
import sys, collections
def load(p):
    g = {}
    for line in open(p):
        f = line.rstrip('\n').split(' ')
        if len(f) < 6: continue
        st, size, ch, ox, oy = f[0], int(f[1]), int(f[2]), int(f[3]), int(f[4])
        rows = f[5].split('/') if f[5] else []
        g[(st, size, ch)] = (ox, oy, rows)
    return g
def inks(ox, oy, rows):
    out = {}
    for r, row in enumerate(rows):
        cols = [ox + i for i, c in enumerate(row) if c == '#']
        if cols: out[oy - 1 - r] = cols  # key: row height above the baseline (0 = first row above it)
    return out
G = load(sys.argv[1])
stats = collections.defaultdict(collections.Counter); exact = collections.Counter(); total = collections.Counter()
for (st, size, ch), v in G.items():
    if st != 'italic' or ch > 0x7e: continue
    up = G.get(('regular', size, ch))
    if not up: continue
    a, b = inks(*v), inks(*up)
    for y in a:
        if y not in b: continue
        total[size] += 1
        sh = {x - b[y][0] for x in [a[y][0]]}
        s = a[y][0] - b[y][0]
        if [x - s for x in a[y]] == b[y]: exact[size] += 1; stats[(size, y)][s] += 1
for size in sorted(total):
    print(size, 'rows', total[size], 'italic row == shifted upright row', exact[size])
    print('  ', ' '.join(f"y{y}:{dict(stats[(size, y)].most_common(3))}" for y in range(-4, size + 1) if stats[(size, y)]))
