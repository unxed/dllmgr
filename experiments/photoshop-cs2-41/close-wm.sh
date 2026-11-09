#!/bin/sh
# #41 repro: start Photoshop CS2 on the stand, wait until loaded, close the
# main window through the window manager (_NET_CLOSE_WINDOW, what Alt+F4 and
# the title-bar cross do), then look for the "Wine C++ Runtime Library" box.
# close-wm.sh OUTDIR [stock|RUNTIME_DIR] [WINEDEBUG] [DOCUMENT]
set -u
OUT=$1; RT=${2:-stock}; DBG=${3:-}; DOC=${4:-}
export DISPLAY=${DISPLAY:-:95} WINEPREFIX=${WINEPREFIX:-/home/claude/work/photoshop-cs2/prefix-auto}
mkdir -p "$OUT"
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
if [ "$RT" = stock ]; then W=/opt/wine-stable/bin/wine; S=/opt/wine-stable/bin/wineserver; set -- DLLMGR27_NO_TRAMPOLINE=1
else W=$RT/bin/wine; S=$RT/bin/wineserver; set -- DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$W WINESERVER=$S WINEDLLOVERRIDES=version=n,b; fi
[ -n "$DBG" ] && set -- "$@" WINEDEBUG="$DBG"
$S -k 2>/dev/null; sleep 2
cd "$PS" && (env "$@" setsid $W Photoshop.exe $DOC > "$OUT/wine.log" 2>&1 &)
# loaded = main frame mapped and the startup critical-section wait is over
i=0; until wmctrl -l | grep -q 'Adobe Photoshop' && [ $i -ge 100 ]; do sleep 2; i=$((i + 2)); [ $i -gt 240 ] && break; done
import -window root "$OUT/1-loaded.png"
wmctrl -c 'Adobe Photoshop'
sleep 8
wmctrl -l > "$OUT/windows-after-close.txt"
import -window root "$OUT/2-after-close.png"
if grep -qi 'runtime' "$OUT/windows-after-close.txt"; then echo "R6025 box: yes"; else echo "R6025 box: no"; fi
pgrep -fa 'Photoshop.exe' | grep -v grep | head -3
