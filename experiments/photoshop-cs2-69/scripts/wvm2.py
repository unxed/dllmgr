from wine_vs_model import *
import sys
path, mode, a, k = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
v = Variant('agg', mode) if not a else CWarp('stem', mode, alpha=a, ends=0)
img = load(path); strip = img[16*k:16*k+20]; m = model(k, v)
d, n, dy, dx = None, 0, 0, 0
best=None
for dy in range(0, strip.shape[0]-m.shape[0]+1):
  for dx in range(8):
    win = strip[dy:dy+m.shape[0], dx:dx+m.shape[1]]; s = np.abs(win-m).sum()
    if best is None or s < best[0]: best=(s,dy,dx)
s,dy,dx=best; win=strip[dy:dy+m.shape[0], dx:dx+m.shape[1]]
np.set_printoptions(linewidth=250)
r = np.argmax(np.abs(win-m).max(2).sum(1))
print('row', r); print('wine ', win[r,:,1][:40]); print('model', m[r,:,1][:40])
print('ink sum wine', (255-win).sum(), 'model', (255-m).sum())
