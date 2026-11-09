#!/bin/sh
# #36 probe runner: ulw-alpha.exe on stock Wine or a runtime dir, screenshot after 6 s (stand :95).
# Result 2026-11-09: correct per-pixel alpha in all four cases (stock/runtime x unmanaged/managed).
# run.sh LABEL WINE_RUNTIME_DIR|stock [managed]
L=$1; RT=$2; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto
if [ "$RT" = stock ]; then W=/opt/wine-stable/bin/wine; S=/opt/wine-stable/bin/wineserver; E=""; else W=$RT/bin/wine; S=$RT/bin/wineserver; E="WINEARCH=wow64 WINELOADER=$W WINESERVER=$S"; fi
(env $E setsid $W /home/claude/work/ulw/ulw-alpha.exe "15 $3" >/dev/null 2>&1 &)
sleep 6; import -window root -crop 1400x1000+0+0 -resize 40% /home/claude/work/ulw/ulw-$L.png
timeout 10 $S -k; sleep 1
