#!/bin/sh
# zoom47b.sh OUT: (Photoshop already showing C:\ps47.png) one Alt+wheel notch at the image centre, 60 fps capture,
# prints when the screen changed after the notch (#47)
O=$1; mkdir -p $O; rm -f $O/*.png; export DISPLAY=:95
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; xdotool mousemove 900 700; sleep 1
ffmpeg -loglevel error -f x11grab -framerate 60 -video_size 3072x1728 -i :95 -t 2 -vf "crop=2000:1500:100:150,scale=500:375" $O/f%03d.png &
FF=$!; sleep 0.5; xdotool keydown alt click 4 keyup alt; wait $FF
python3 - $O <<'PY'
import sys, glob
from PIL import Image
import numpy as np
fs = sorted(glob.glob(sys.argv[1] + '/f*.png')); prev = None; ch = []
for i, f in enumerate(fs):
    a = np.array(Image.open(f).convert('L')).astype(int)
    if prev is not None:
        n = int((abs(a - prev) > 20).sum())
        if n > 50: ch.append((i, n))
    prev = a
print('changed frames (index at 60 fps, changed px):', ch)
if ch: print('first->last change: %d ms' % ((ch[-1][0] - ch[0][0]) * 1000 // 60))
PY
