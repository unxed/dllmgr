#!/bin/sh
# #49: does Ctrl+N (physical N key) open "New" in Photoshop CS2 when the
# Russian layout is active? Stand :95, layouts us,ru.
# hotkey.sh START_GROUP PRESS_GROUP [stock|RUNTIME_DIR]
#   START_GROUP: layout group active when Photoshop starts (0 us, 1 ru)
#   PRESS_GROUP: layout group active when Ctrl+N is pressed
H=$(cd "$(dirname "$0")" && pwd)
SG=$1; PG=$2; RT=${3:-stock}
export DISPLAY=${DISPLAY:-:95} WINEPREFIX=${WINEPREFIX:-/home/claude/work/photoshop-cs2/prefix-auto}
if [ "$RT" = stock ]; then W=/opt/wine-stable/bin/wine; S=/opt/wine-stable/bin/wineserver; set -- DLLMGR27_NO_TRAMPOLINE=1
else W=$RT/bin/wine; S=$RT/bin/wineserver; set -- DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$W WINESERVER=$S WINEDLLOVERRIDES=version=n,b; fi
setxkbmap -layout "${LAYOUT:-us,ru}"
$S -k 2>/dev/null; sleep 1
python3 "$H/xkbgroup.py" "$SG" >/dev/null
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" && (env "$@" ${WDEBUG:+WINEDEBUG=$WDEBUG} setsid $W Photoshop.exe >"${LOG:-/dev/null}" 2>&1 &)
sleep 100
xdotool mousemove 1788 1372 click 1   # trial activation dialog: Continue Trial
sleep 4
wmctrl -c 'Adobe Updater Preferences'; sleep 2
F=$(xdotool search --name '^Adobe Photoshop$' | head -1)
xdotool windowactivate --sync "$F"
python3 "$H/xkbgroup.py" "$PG" >/dev/null
# keys are sent as keycodes (physical keys): N=57, B=56 on evdev; a keysym
# name would make xdotool pick whatever group has that keysym
if [ "${KEY:-ctrl+57}" = ctrl+57 ]; then
xdotool key ctrl+57
sleep 3
if wmctrl -l | grep -q ' New$'; then echo "start=$SG press=$PG: New opened"; else echo "start=$SG press=$PG: NOTHING"; fi
# text input check: the New dialog's Name field has focus; type the N key
[ -n "${TYPE:-}" ] && { xdotool key 57; sleep 1; import -window root -crop 1300x500+900+500 +repage "${OUT:-/tmp}/typed.png"; }
else
# single-key tool shortcut: compare the tool options bar before/after
import -window root -crop 1500x60+0+110 +repage "${OUT:-/tmp}/opt-before.png"
xdotool key "$KEY"; sleep 2
import -window root -crop 1500x60+0+110 +repage "${OUT:-/tmp}/opt-after.png"
D=$(compare -metric AE "${OUT:-/tmp}/opt-before.png" "${OUT:-/tmp}/opt-after.png" null: 2>&1)
echo "start=$SG press=$PG key=$KEY: options bar changed pixels $D"
fi
python3 "$H/xkbgroup.py" 0 >/dev/null
$S -k
