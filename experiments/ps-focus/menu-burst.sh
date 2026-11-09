#!/bin/sh
# burst.sh OUTDIR [env...]: start Photoshop (Muffin stand :95), walk menus, burst-capture, rank black fraction
B=$1; shift; mkdir -p $B; export DISPLAY=${DISPLAY:-:95} WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto
W=${WINE:-/opt/wine-stable/bin/wine}; S=$(dirname $W)/wineserver
$S -k 2>/dev/null; sleep 1
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
env "$@" WINEDLLOVERRIDES=version=n,b setsid $W "$exe" >$B.log 2>&1 &
sleep 110
(for i in $(seq 40); do import -window root -crop 900x1000+0+60 -resize 40% $B/$(printf %02d $i).png; done) &
CAP=$!
for k in 1 2 3; do xdotool mousemove 36 84; [ $k = 1 ] && xdotool click 1; sleep .5; xdotool mousemove 100 84; sleep .5; xdotool mousemove 176 84; sleep .5; xdotool mousemove 100 84; sleep .5; done; wait $CAP
n=0; for f in $B/*.png; do v=$(convert $f -colorspace gray -threshold 3% -format '%[fx:1-mean]' info:); [ $(echo "$v > 0.1" | bc) = 1 ] && n=$((n+1)); done
echo "$(basename $B) $*: frames with >10% black: $n/40"
xdotool key Escape; $S -k
