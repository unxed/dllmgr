"""C agg_place_run (extracted from the edited graphics.c into ctest/place.c) vs cmodel.place"""
import subprocess
from measure import WORDS, FONTS
import cmodel
inp = []; exp = []
for style in ('regular', 'bold'):
    for ppem in (10, 11):
        f = FONTS[(style, ppem)]
        for alpha in (128, 192):
            for w in WORDS:
                rows = [str(len(w))]
                for c in w:
                    lin, app = f.metrics(c)
                    e = [cmodel.edges(f, c, (ph * 64 + 1) // 3, alpha) for ph in range(3)]
                    rows.append(f"{lin} {app} " + ' '.join(f"{a} {b}" for a, b in e))
                inp.append(' '.join(rows))
                exp.append([wh * 3 + ((s * 3 + 32) // 64) for wh, s in cmodel.place(f, w, alpha, ends=32)])
out = subprocess.run(['ctest/place'], input='\n'.join(inp) + '\n', capture_output=True, text=True).stdout.split('\n')
print(sum(list(map(int, o.split())) == e for o, e in zip(out, exp)), '/', len(exp), 'runs placed identically')
