#!/bin/sh
# blurtest.sh LABEL [env...]: #46. Photoshop with C:\t46.png (Muffin :95), blur tool, move across the canvas,
# compare the canvas region with the same region before the moves; prints changed pixel count.
L=$1; shift; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; C=/home/claude/work/cur
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
(cd "$D" && env "$@" setsid /opt/wine-stable/bin/wine Photoshop.exe 'C:\t46.png' >$C/blur-$L.log 2>&1 &)
sleep 100; xdotool mousemove 48 552 click 1; sleep 1; xdotool mousemove 1500 1300; sleep 1
import -window root -crop 900x450+500+450 $C/blur-$L-0.png
xdotool mousemove 600 600; sleep .3
for i in $(seq 0 40); do xdotool mousemove $((600+i*15)) $((600+i*5)); sleep .03; done
xdotool mousemove 1500 1300; sleep 1.5
import -window root -crop 900x450+500+450 $C/blur-$L-1.png
echo "$L $*: changed pixels $(compare -metric AE $C/blur-$L-0.png $C/blur-$L-1.png null: 2>&1)"
timeout 10 /opt/wine-stable/bin/wineserver -k; sleep 1
