#!/bin/sh
# t73b.sh OUT: FastStone like `dllmgr run` (DLLMGR_TARGET_EXE set), Settings (F12), screenshot; DLLMGR73_ASSOC touches OUT/hit
OUT=$1; mkdir -p $OUT; RT=/home/claude/work/rt-cur3
export DISPLAY=:96 WINEPREFIX=/home/claude/work/fs40/prefix WINEDEBUG=-all
$RT/bin/wineserver -k 2>/dev/null; sleep 1
(env DLLMGR_TARGET_EXE='C:\x\FSViewer.exe' DLLMGR73_ASSOC="touch $OUT/hit" WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=msimg32=n,b setsid $RT/bin/wine /home/claude/work/fs40/FSViewer85/FSViewer.exe > $OUT/wine.log 2>&1 &)
sleep 15; import -window root $OUT/1-browser.png
xdotool key F12; sleep 5; import -window root $OUT/2-settings.png
wmctrl -l | cut -c20-
