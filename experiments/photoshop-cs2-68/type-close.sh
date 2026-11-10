#!/bin/sh
# t41.sh OUT MODE(exit|close): start plain, File>Open C:\ps47.png, then exit; look for R6025
OUT=$1; MODE=$2; mkdir -p $OUT
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8
setxkbmap -layout us,ru
${RT:-/opt/wine-stable}/bin/wineserver -k 2>/dev/null; sleep 1
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
if [ -n "$RT" ]; then
  (env DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WD:--all} setsid $RT/bin/wine Photoshop.exe > $OUT/wine.log 2>&1 &)
else
  (setsid /opt/wine-stable/bin/wine Photoshop.exe > $OUT/wine.log 2>&1 &)
fi
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1770 1359 click 1; sleep 5
wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
xdotool key ctrl+o; sleep 4
xdotool key --delay 120 backslash p s 4 7 period p n g; xdotool key Return; sleep 8
wmctrl -l > $OUT/w1.txt; import -window root $OUT/1-open.png
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
if [ $MODE = exit ]; then xdotool key ctrl+q
elif [ $MODE = closeimg ]; then
  for f in t46 ps47 t46 ps47 t46 ps47; do
    xdotool key ctrl+w; sleep 3; wmctrl -l | grep -i "6025\|runtime" && break
    F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
    xdotool key ctrl+o; sleep 3; xdotool key --delay 120 backslash $(echo $f | sed 's/./& /g') period p n g; xdotool key Return; sleep 6
    wmctrl -l | cut -c20-80 | grep "@" ; F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"
  done
elif [ $MODE = type ]; then
  xdotool key t; sleep 3; xdotool mousemove 900 900; sleep 1; xdotool mousedown 1; sleep 0.3; xdotool mouseup 1; sleep 4; xdotool type --delay 80 abc; sleep 2
  import -window root $OUT/1b-typing.png
  if [ -n "$DOCX" ]; then xdotool mousemove $DOCX click 1; else xdotool key ctrl+w; fi
else wmctrl -c 'Adobe Photoshop'; fi
sleep 8; wmctrl -l > $OUT/w2.txt; import -window root $OUT/2-exit.png
[ -n "$KEEP" ] && exit 0
grep -i "r6025\|runtime\|pure virtual\|error" $OUT/w2.txt; grep -c "" $OUT/w2.txt
pgrep -f Photoshop.exe >/dev/null && echo "still running" || echo "exited"
grep -i "6025\|pure virtual\|exception" $OUT/wine.log | head -3
${RT:-/opt/wine-stable}/bin/wineserver -k 2>/dev/null
