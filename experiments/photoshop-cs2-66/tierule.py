exec(open('/home/claude/work/kern66/stitch.py').read().split('G = load(sys.argv[1])')[0])
import math
def runs(up, y):
    xs = sorted(x for x, yy in up if yy == y); out = []
    for x in xs:
        if out and x == out[-1][1] + 1: out[-1][1] = x
        else: out.append([x, x])
    return out
def ital2(up, mode='shrink'):
    out = set()
    for y in {y for _, y in up}:
        v = (y + 0.5) / 3; k = math.floor(v); tie = abs(v - k - 0.5) < 1e-9
        for a, b in runs(up, y):
            if not tie: s = rnd(v); out |= {(x + s, y) for x in range(a, b + 1)}
            elif b > a: out |= {(x, y) for x in range(a + k + 1, b + k + 1)}  # [a+k+1, b+k]
            else: out.add((a + k + 1, y))
    return out
