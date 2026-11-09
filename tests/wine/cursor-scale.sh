#!/bin/sh
# #44 probe: size of the X cursor of a DPI-unaware window with a 32x32 custom
# cursor. Needs DISPLAY (Xvfb, any size), xdotool, python3 with libXfixes, and
# WINEPREFIX with HKCU\Control Panel\Desktop LogPixels=192.
#   tests/wine/cursor-scale.sh RUNTIME_DIR mono|color
# Expected at 192 DPI: 64x64 with dllmgr-44.patch (hot 30,30 mono / 8,8 color),
# 32x32 without it or with DLLMGR44_NO_CURSOR_SCALE=1.
set -e
RT=$1; here=$(cd "$(dirname "$0")" && pwd); exe=${CURSOR_EXE:-/tmp/cursor-scale.exe}
[ -f "$exe" ] || x86_64-w64-mingw32-gcc -O2 -mwindows -o "$exe" "$here/cursor-scale.c"
WINEARCH=wow64 WINEDEBUG=-all WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $RT/bin/wine "$exe" $2 25 >/dev/null 2>&1 &
t=0; until xdotool search --onlyvisible --name cursor44 >/dev/null 2>&1 || [ $t -ge 300 ]; do sleep .1; t=$((t+1)); done
sleep 2; xdotool mousemove 100 100; sleep .3; xdotool mousemove 120 120; sleep 1
echo "$(basename "$RT") $2: $(python3 "$here/xcursor-size.py")"
"$RT/bin/wineserver" -k
