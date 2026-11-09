#!/bin/sh
RT=/home/claude/work/rt-focus
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
O=/home/claude/work/shape/focus2.txt; : > $O
WINEDLLOVERRIDES=version=n,b WINEDEBUG=+timestamp,+x11drv,+event WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $RT/bin/wine "$exe" >/dev/null 2>/home/claude/work/shape/focus2.log &
until xdotool search --onlyvisible --class photoshop.exe >/dev/null 2>&1; do sleep .1; done
sleep 25; f=$(xdotool getwindowfocus); echo "no switch: focus=$f '$(xdotool getwindowname $f)'" >> $O
xlogo -geometry 300x300+10+10 & sleep 1; xl=$(xdotool search --onlyvisible --class xlogo | head -1); timeout 5 xdotool windowactivate $xl; sleep 2
echo "after xlogo: focus=$(xdotool getwindowfocus) xlogo=$xl" >> $O
sleep 70; date +%s.%N >> $O; main=$(xdotool search --onlyvisible --name '^Adobe Photoshop$' | head -1); echo CLICK; xdotool mousemove 300 1500 click 1; sleep 2
f=$(xdotool getwindowfocus); echo "after click on Photoshop: focus=$f '$(xdotool getwindowname $f)'" >> $O
$RT/bin/wineserver -k
