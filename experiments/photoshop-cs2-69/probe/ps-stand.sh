#!/bin/sh
# ps.sh TAG [ENV...]: Photoshop CS2 on rt-cur3 (stand :95) with C:\t46.png, agg-rgb; leaves it running
T=$1; shift; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; RT=/home/claude/work/rt-cur3
O=/tmp/claude-0/-home-claude/71c1be2e-9f14-5b87-94fa-9d3adfcbd591/scratchpad/stem/ps; mkdir -p $O
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
$RT/bin/wineserver -k 2>/dev/null; sleep 1
cd "$PS"
(env "$@" DLLMGR52_TEXT=agg-rgb DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=-all setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > $O/$T.log 2>&1 &)
