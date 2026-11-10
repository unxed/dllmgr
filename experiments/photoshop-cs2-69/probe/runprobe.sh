#!/bin/sh
# runprobe.sh OUT.bmp [ENV...]: stem-words.exe on rt-cur3 (headless :95)
O=$1; shift; cd /tmp/claude-0/-home-claude/71c1be2e-9f14-5b87-94fa-9d3adfcbd591/scratchpad/stem
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; RT=/home/claude/work/rt-cur3
$RT/bin/wineserver -k 2>/dev/null; sleep 1
env "$@" WINEARCH=wow64 WINEDEBUG=-all WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $RT/bin/wine ./stem-words.exe "$O"
$RT/bin/wineserver -k 2>/dev/null
