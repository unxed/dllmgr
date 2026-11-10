#!/bin/sh
# t40.sh OUT [RT]: FastStone fullscreen viewer, Esc with "confirm on Esc exit" on; is the confirmation on top?
OUT=$1; RT=${2:-/opt/wine-stable}; mkdir -p $OUT
export DISPLAY=:95 WINEPREFIX=/home/claude/work/fs40/prefix WINEDEBUG=-all
$RT/bin/wineserver -k 2>/dev/null; sleep 1
(env DLLMGR27_OFF=1 WINEDLLOVERRIDES=msimg32=b WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver setsid $RT/bin/wine /home/claude/work/fs40/FSViewer85/FSViewer.exe 'Z:\home\claude\work\tramp\a.jpg' > $OUT/wine.log 2>&1 &)
sleep 12; import -window root $OUT/1-viewer.png
xdotool key Escape; sleep 3
for w in $(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //;s/,//g'); do echo "$w $(xprop -id $w WM_NAME _NET_WM_STATE | tr '\n' ' ' | cut -c1-160)"; done > $OUT/stack.txt
cat $OUT/stack.txt
import -window root $OUT/2-esc.png
$RT/bin/wineserver -k 2>/dev/null
