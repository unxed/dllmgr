from wine_vs_model import *
for path, kind in [('p-agg-rgb-s0.bmp', 0), ('p-agg-rgb-s1.bmp', 128)]:
    img = load(path); worst = 0; n = 0; exact = 0
    for k, strip in lines(img):
        if k >= 64: continue
        res = []
        for v in (Variant('agg', 'rgb'), CWarp("stem", "rgb", alpha=128, ends=32)):
            m = model(k, v); best = None
            for dy in range(0, strip.shape[0] - m.shape[0] + 1):
                for dx in range(8):
                    win = strip[dy:dy + m.shape[0], dx:dx + m.shape[1]]
                    d = int(np.abs(win - m).max())
                    if best is None or d < best: best = d
            res.append(best)
        mine = res[1 if kind else 0]; other = res[0 if kind else 1]
        worst = max(worst, mine); exact += mine == 0; n += other > 0
    print(path, 'regular lines: max|diff| vs its model', worst, '; identical lines', exact, '/64 ; lines where the other variant differs', n)
