#!/bin/sh
RT=/home/claude/work/rt-focus
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
WINEDLLOVERRIDES=version=n,b WINEDEBUG=+timestamp,+x11drv,+event WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $RT/bin/wine "$exe" >/dev/null 2>/home/claude/work/shape/mini.log &
until xdotool search --onlyvisible --class photoshop.exe >/dev/null 2>&1; do sleep .1; done
sleep 3; echo "MINIMIZE $(date +%s.%N)" > /home/claude/work/shape/mini.txt
main=$(xdotool search --onlyvisible --name '^Adobe Photoshop$' | head -1); xdotool windowminimize $main; sleep 3
for w in $(xdotool search --onlyvisible --class photoshop.exe); do eval "$(xdotool getwindowgeometry --shell $w)"; echo "visible $w ${WIDTH}x$HEIGHT '$(xdotool getwindowname $w)'" >> /home/claude/work/shape/mini.txt; done
for w in $(xdotool search --onlyvisible --class photoshop.exe); do echo "== $w"; xprop -id $w WM_TRANSIENT_FOR _NET_WM_WINDOW_TYPE _NET_WM_STATE WM_HINTS 2>&1 | head -6; done >> /home/claude/work/shape/mini.txt; xprop -id $main WM_STATE >> /home/claude/work/shape/mini.txt
$RT/bin/wineserver -k
