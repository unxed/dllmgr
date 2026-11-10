#!/bin/sh
# first-type.sh TAG: fresh Photoshop, wait for the document, select the Type tool once, then sample the canvas
# under the mouse every 0.25 s for 12 s; prints the time when the I-beam appears (#70)
T=$1; D=/home/claude/work/c70; export DISPLAY=:95
/home/claude/work/r41/start-ps.sh $T >/dev/null 2>&1
timeout 300 sh -c 'until wmctrl -l | grep -q "t46.png @"; do sleep 2; done'; sleep 10
xdotool mousemove 1000 800; sleep 2; import -window root -crop 80x80+960+760 $D/$T-base.png
xdotool mousemove 105 603 click 1; sleep 0.2; xdotool mousemove 1000 800
start=$(date +%s%N)
for i in $(seq 0 47); do import -window root -crop 80x80+960+760 $D/$T-$i.png; echo "$i $(( ($(date +%s%N) - start) / 1000000 ))" >> $D/$T-times.txt; sleep 0.25; done
python3 - "$D" "$T" <<'PY'
import sys; from PIL import Image; import numpy as np
D, T = sys.argv[1:]
base = np.array(Image.open(f'{D}/{T}-base.png').convert('L')).astype(int)
times = dict(l.split() for l in open(f'{D}/{T}-times.txt'))
for i in range(48):
    a = np.array(Image.open(f'{D}/{T}-{i}.png').convert('L')).astype(int)
    # the I-beam's dotted box is light grey: count bright pixels that were not there before
    n = int(((a > 180) & (base < 150)).sum())
    if n > 40: print(f'{T}: I-beam visible at sample {i}, {times[str(i)]} ms after the click ({n} px)'); break
else: print(f'{T}: no I-beam within 12 s')
PY
