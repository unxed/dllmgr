#!/bin/sh
# mini4.sh DLL LABEL: Muffin :95; swap the proxy, minimize main during loading, report splash; restore
DLL=$1; L=$2; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cp "$DLL" "$D/version.dll"
(env $EXTRA WINEDLLOVERRIDES=version=n,b setsid /opt/wine-stable/bin/wine "$D/Photoshop.exe" >/home/claude/work/cur/mini4-$L.log 2>&1 &)
t=0; until xdotool search --onlyvisible --name '^Adobe Photoshop$' >/dev/null 2>&1 || [ $t -ge 300 ]; do sleep .2; t=$((t+1)); done
sleep 0.3; main=$(xdotool search --onlyvisible --name '^Adobe Photoshop$' | head -1)
import -window root -resize 20% /home/claude/work/cur/mini4-$L-0.png
splash=$(for w in $(xdotool search --class photoshop.exe); do xwininfo -id $w | grep -q IsViewable && xprop -id $w WM_TRANSIENT_FOR 2>/dev/null | grep -q 'window id' && echo $w; done | head -1)
echo "$L splash: $(xwininfo -id $splash | grep -i 'override\|Map State' | tr -s ' \n' ' ') $(xprop -id $splash WM_STATE | sed -n 2p | tr -d '\t')"
xdotool windowminimize $main; sleep 3
import -window root -resize 20% /home/claude/work/cur/mini4-$L-1.png
echo "$L minimized: main $(xprop -id $main WM_STATE | sed -n 2p | tr -d '\t'); splash $(xprop -id $splash WM_STATE | sed -n 2p | tr -d '\t')"
xdotool windowactivate $main; sleep 3
import -window root -resize 20% /home/claude/work/cur/mini4-$L-2.png
echo "$L restored: main $(xprop -id $main WM_STATE | sed -n 2p | tr -d '\t'); splash $(xprop -id $splash WM_STATE | sed -n 2p | tr -d '\t')"
timeout 5 /opt/wine-stable/bin/wineserver -k; sleep 1
cp /home/claude/work/cur/version-current.dll "$D/version.dll"
