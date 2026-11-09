#!/bin/sh
# over.sh DLL LABEL: does the splash stay above another app's window? (Muffin :95)
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cp "$1" "$D/version.dll"
(WINEDLLOVERRIDES=version=n,b setsid /opt/wine-stable/bin/wine "$D/Photoshop.exe" >/dev/null 2>&1 &)
t=0; until xdotool search --onlyvisible --name '^Adobe Photoshop$' >/dev/null 2>&1 || [ $t -ge 300 ]; do sleep .2; t=$((t+1)); done; sleep 1
xlogo -geometry 1400x1000+800+400 & sleep 2; timeout 5 xdotool windowactivate $(xdotool search --onlyvisible --class xlogo | head -1); sleep 2
import -window root -resize 20% over-$2.png; echo "$2 focus: $(xdotool getwindowfocus getwindowname)"
kill %1 2>/dev/null; pkill xlogo; timeout 5 /opt/wine-stable/bin/wineserver -k; sleep 1; cp /home/claude/work/cur/version-current.dll "$D/version.dll"
