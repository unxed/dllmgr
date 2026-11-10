#!/bin/sh
# startup-error.sh OUT: start Photoshop with a document (RT, WINEPREFIX as in
# t78p.sh), pass the trial dialog, report whether the "program error" box is
# up (F26). Extra env for the experiment goes through EXTRA="VAR=x ...".
OUT=$1; mkdir -p "$OUT"
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $EXTRA "$@"; }
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe ${DOC-'C:\t46.png'} > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
import -window root "$OUT/0-activation.png"
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 8; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
wmctrl -l | cut -c20- > "$OUT/windows.txt"
n=$(grep -c '^Adobe Photoshop$' "$OUT/windows.txt")
[ "$n" -ge 2 ] && echo "program error: YES" || echo "program error: no"
import -window root "$OUT/1-started.png"
w $RT/bin/wineserver -k
