#!/bin/sh
# z16.sh OUT [extra env]: Photoshop (rt-cur3, prefix-b, :96) opens C:\t46.png (16-bit) and zooms 3 notches; 60 fps capture per notch
OUT=$1; shift; mkdir -p $OUT; RT=/home/claude/work/rt-cur3
export DISPLAY=:96 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-b
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
$RT/bin/wineserver -k 2>/dev/null; sleep 1; cd "$PS"
(env "$@" DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=-all setsid $RT/bin/wine Photoshop.exe > $OUT/wine.log 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1770 1359 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 1
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
xdotool key ctrl+o; sleep 4; xdotool key --delay 120 backslash t 4 6 period p n g; xdotool key Return; sleep 8
wmctrl -l | cut -c20-80 | grep "@"
for n in 1 2 3; do
  rm -f $OUT/n$n-*.png; xdotool mousemove 900 700; sleep 1
  ffmpeg -loglevel error -f x11grab -framerate 60 -video_size 3072x1728 -i :96 -t 2 -vf "crop=2000:1500:100:150,scale=500:375" $OUT/n$n-%03d.png &
  FF=$!; sleep 0.5; xdotool keydown alt click 4 keyup alt; wait $FF; sleep 1
done
python3 - $OUT <<'PY'
import sys, glob
from PIL import Image
import numpy as np
for n in (1,2,3):
    fs = sorted(glob.glob(sys.argv[1] + '/n%d-*.png' % n)); arr=[np.array(Image.open(f).convert('L')).astype(int) for f in fs]
    final=arr[-1]; ch=[]
    for i in range(1,len(arr)):
        d=int((abs(arr[i]-arr[i-1])>20).sum())
        if d>50: ch.append((i,d,int((abs(arr[i]-final)>20).sum())))
    print('notch',n,'changes (frame, changed px, px still != final):',ch)
PY
$RT/bin/wineserver -k
