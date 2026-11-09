#!/bin/sh
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
O=/home/claude/work/shape/focus.txt; : > $O
WINEDLLOVERRIDES=version=n,b DLLMGR27_DEBUG=1 WINEDEBUG=+timestamp,+x11drv,+event /opt/wine-stable/bin/wine "$exe" >/dev/null 2>/home/claude/work/shape/focus.log &
t=0; until xdotool search --onlyvisible --class photoshop.exe >/dev/null 2>&1 || [ $t -ge 600 ]; do sleep .1; t=$((t+1)); done
echo "ps visible after $t ticks" >> $O
sleep 3; xlogo -geometry 300x300+10+10 & sleep 1
xl=$(xdotool search --onlyvisible --class xlogo | head -1); timeout 5 xdotool windowactivate $xl; echo "xlogo=$xl activated $(date +%s.%N | cut -c1-14)" >> $O
for i in $(seq 60); do f=$(xdotool getwindowfocus 2>/dev/null); echo "$(date +%s.%N | cut -c1-14) focus=$f" >> $O; sleep .5; done
/opt/wine-stable/bin/wineserver -k
