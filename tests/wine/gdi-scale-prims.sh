#!/bin/sh
# run.sh TAG [ENV...]: prims.exe on rt-cur3, capture of its client window -> TAG.png
T=$1; shift; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; RT=/home/claude/work/rt-cur3
$RT/bin/wineserver -k 2>/dev/null; sleep 1
(env "$@" WINEARCH=wow64 WINEDEBUG=-all WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver setsid $RT/bin/wine ${PRIMS_EXE:-/home/claude/work/prims/prims.exe} > /home/claude/work/prims/$T.log 2>&1 &)
for i in $(seq 1 40); do W=$(xdotool search --name '^prims$' 2>/dev/null | head -1); [ -n "$W" ] && break; sleep 0.5; done
sleep 2; import -window "$W" /home/claude/work/prims/$T.png; identify /home/claude/work/prims/$T.png
