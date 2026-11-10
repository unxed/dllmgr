#!/bin/sh
# t78.sh OUT: Photoshop (rt-cur3, prefix-b, :96) with a document; a big xclock; Alt+Tab to it; are the palettes still on top?
OUT=$1; mkdir -p $OUT; RT=/home/claude/work/rt-cur3
export DISPLAY=:96 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-b
pgrep -f "muffin --sm-disable" >/dev/null || (setsid dbus-run-session -- muffin --sm-disable --x11 --replace > $OUT/wm.log 2>&1 &); sleep 2
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
$RT/bin/wineserver -k 2>/dev/null; sleep 1; cd "$PS"
(env DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=-all setsid $RT/bin/wine Photoshop.exe > $OUT/wine.log 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1770 1359 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 1
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
xdotool key ctrl+o; sleep 4; xdotool key --delay 120 backslash p s 4 7 period p n g; xdotool key Return; sleep 8
(xclock -geometry 3000x1650+30+30 &); sleep 2
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2
xdotool mousemove 2780 800 click 1; sleep 2   # a history state in the History palette
import -window root $OUT/1-ps.png
wmctrl -a xclock; sleep 3
import -window root $OUT/2-after-alttab.png
xprop -root _NET_ACTIVE_WINDOW
for w in $(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //;s/,//g'); do echo "$w $(xprop -id $w WM_NAME _NET_WM_STATE WM_CLASS 2>/dev/null | tr '\n' ' ' | cut -c1-150)"; done
xwininfo -root -children | grep -i 'photoshop\|xclock\|has no name' | head -20 > $OUT/xtree.txt
for w in $(xwininfo -root -children | awk '/0x/{print $1}'); do xwininfo -id $w | grep -q 'Override Redirect State: yes' && xwininfo -id $w -stats | grep -E 'Window id|Map State|Absolute upper-left|Width|Height' | tr '\n' ' ' && echo; done > $OUT/override.txt
pkill xclock; $RT/bin/wineserver -k
