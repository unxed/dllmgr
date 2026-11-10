#!/usr/bin/env python3
"""#66: pair gaps (white pixels between letter ink) of a measured metrics66.csv
vs Windows. gapcsv.py WINDOWS.csv WINE.csv [style] -> per size: pairs that
differ, sum|diff|, glued where Windows has a gap, word width % vs Windows."""
import csv, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
WORDS = ["Open", "Background", "History", "Layers", "Channels", "Paths", "Actions", "Navigator", "Info",
         "Histogram", "Color", "Swatches", "Styles", "Brushes", "Tool Presets", "Layer Comps", "Opacity", "Fill",
         "Normal", "Lock", "lena.jpeg", "Snapshot", "Merge Visible", "New Layer", "Duplicate", "Image", "Select"]
load = lambda p: {(r['style'], int(r['size']), int(r['char'])): (int(r['left']), int(r['width']), int(r['advance']))
                  for r in csv.DictReader(open(p))}
W, N = load(sys.argv[1]), load(sys.argv[2])
style = sys.argv[3] if len(sys.argv) > 3 else 'bold'
def gaps(m, word):
    return [m[ord(a)][2] - m[ord(a)][0] - m[ord(a)][1] + m[ord(b)][0]
            for a, b in zip(word, word[1:]) if ' ' not in (a, b)]
for size in sorted({k[1] for k in W}):
    mw = {ord(c): W[(style, size, ord(c))] for w in WORDS for c in w if c != " "}
    mn = {ord(c): N[(style, size, ord(c))] for w in WORDS for c in w if c != " "}
    bad = tot = glued = diff = 0; ww = wn = 0
    for word in WORDS:
        for x, y in zip(gaps(mw, word), gaps(mn, word)):
            tot += 1; bad += x != y; diff += abs(x - y); glued += y <= 0 < x
        ww += sum(mw[ord(c)][2] for c in word if c != " "); wn += sum(mn[ord(c)][2] for c in word if c != " ")
    print(f"{style} {size}px pairs {tot} differ {bad} sum|diff| {diff} glued {glued} width {100.0 * (wn - ww) / ww:+.1f}%")
