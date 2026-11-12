#!/bin/sh
# End-to-end check of the installed recipe on the stand, the way the owner
# starts Photoshop: plain `wine Photoshop.exe FILE` (system Wine; the launch
# trampoline must hand over to the private runtime). Checks in one start:
#  - handover (dllmgr status: "on the private runtime")      #51
#  - start with a document while preferences exist          #62
#  - splash without halo (screenshot of the card)           #36
#  - Ctrl+N with the Russian layout first (ru,us)           #49
# e2e.sh OUTDIR [FILE]
OUT=$1; DOC=${2:-C:\\t46.png}
H=$(cd "$(dirname "$0")/.." && pwd)
export DISPLAY=${DISPLAY:-:95} WINEPREFIX=${WINEPREFIX:-/home/claude/work/photoshop-cs2/prefix-auto} LC_ALL=C.UTF-8
mkdir -p "$OUT"
if ! xdpyinfo >/dev/null 2>&1; then  # the stand dies between sessions
    rm -f /tmp/.X95-lock /tmp/.X11-unix/X95
    STAND_DISPLAY=:95 STAND_DIR=/home/claude/work/cur/m "$H/../scripts/sandbox-stand.sh" up >/dev/null 2>&1; sleep 2
fi
setxkbmap -layout ru,us
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
(setsid /opt/wine-stable/bin/wine Photoshop.exe "$DOC" > "$OUT/wine.log" 2>&1 &)
sleep 14
import -window root "$OUT/1-splash.png"
sleep 95
~/.local/bin/dllmgr status photoshop-cs2 > "$OUT/status.txt" 2>&1
grep -q 'on the private runtime' "$OUT/status.txt" && echo "handover: private runtime" || echo "handover: NO"
xdotool mousemove 1788 1372 click 1; sleep 4                 # trial: Continue Trial
wmctrl -c 'Adobe Updater Preferences'; sleep 2
wmctrl -l > "$OUT/windows.txt"
grep -q 'hardware or system' "$OUT/windows.txt" && echo "document: ERROR BOX"
grep -q ' @ [0-9][0-9.,]*%' "$OUT/windows.txt" && echo "document: open" || echo "document: NOT OPEN"
import -window root "$OUT/2-loaded.png"
F=$(xdotool search --name '^Adobe Photoshop$' | head -1)
xdotool windowactivate --sync "$F"
xdotool key ctrl+57; sleep 3                                  # physical N
wmctrl -l | grep -q ' New$' && echo "ru Ctrl+N: New opened" || echo "ru Ctrl+N: NOTHING"
import -window root "$OUT/3-ctrl-n.png"
setxkbmap -layout us,ru
/opt/wine-stable/bin/wineserver -k
