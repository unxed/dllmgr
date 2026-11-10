#!/bin/sh
# tstart.sh [env...]: seconds from launch to the trial Activation dialog (rt-cur3, prefix-b, :96)
RT=/home/claude/work/rt-cur3; export DISPLAY=:96 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-b
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
$RT/bin/wineserver -k 2>/dev/null; sleep 1; cd "$PS"; T0=$(date +%s%N)
(env "$@" DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=-all setsid $RT/bin/wine Photoshop.exe > /dev/null 2>&1 &)
while ! wmctrl -l 2>/dev/null | grep -q Activation; do sleep 0.2; [ $(( ($(date +%s%N)-T0)/1000000000 )) -gt 240 ] && break; done
echo "activation dialog after $(( ($(date +%s%N)-T0)/1000000 )) ms ($*)"
$RT/bin/wineserver -k
