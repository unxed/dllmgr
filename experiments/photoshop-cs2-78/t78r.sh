#!/bin/sh
# t78r.sh OUT: #78 retest after the owner's v23 report (2026-11-11): click
# into a palette (History) and, separately, into the toolbox, then switch to
# a normal app (a big xterm) like Alt+Tab in Cinnamon, and dump the X
# stacking (stack.py, _NET_CLIENT_LIST_STACKING, xwininfo -tree), the Win32
# z-order with WS_EX_TOPMOST (PROBE = zlist78.exe) and screenshots.
# Env: RT, WINEPREFIX, PROBE, WDBG, DISMISS=1 (F26 box), EXTRA (env for
# Photoshop), SW = emu (alttab-emu.py, default) | wmctrl | key (xdotool
# alt+Tab) | keyhold (Alt held 1.8 s, Cinnamon shows its switcher),
# HIST / TOOL ("X Y" of a History row / a toolbox button).
OUT=$1; mkdir -p "$OUT"; HIST=${HIST:-2780 800}; TOOL=${TOOL:-50 260}; SW=${SW:-emu}
E=$(dirname "$(readlink -f "$0")")
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
dump() {
	"$E/stack.py" > "$OUT/$1-stack.txt" 2>&1
	xprop -root _NET_CLIENT_LIST_STACKING >> "$OUT/$1-stack.txt"
	xwininfo -root -tree > "$OUT/$1-tree.txt" 2>&1
	w WINEDEBUG=-all $RT/bin/wine "$PROBE" > "$OUT/$1-probe.txt" 2>/dev/null
	# Photoshop windows the X server shows above the terminal's frame
	n=$(awk '/TERM"/ {exit} /photoshop/ {n++} END {print n+0}' "$OUT/$1-stack.txt")
	echo "$1: $(head -1 "$OUT/$1-probe.txt"); photoshop X windows above TERM: $n"
	grep -E 'PSFloatC|Photoshop ' "$OUT/$1-probe.txt" | grep 'vis=1' | cut -c1-60 | sed 's/^/    /'
}
switch() {
	case $SW in
	emu) "$E/alttab-emu.py" "$T" ;;
	wmctrl) wmctrl -i -a "$T" ;;
	key) xdotool key alt+Tab ;;
	keyhold) xdotool keydown alt; sleep 0.3; xdotool key Tab; sleep 1.5; xdotool keyup alt ;;
	esac
	sleep 3
}
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} $EXTRA setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
if [ -n "$DISMISS" ]; then
	for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
	for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
		xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
	done
fi
(xterm -geometry 500x125+20+20 -title TERM &); sleep 3
T=$(xdotool search --name '^TERM$' | head -1)
ps_front() { F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2; }
ps_front
dump 0-before
xdotool mousemove $HIST click 1; sleep 2
dump 1-hist-click
switch
dump 2-hist-switched
import -window root -resize 25% "$OUT/2-hist-switched-25pct.png"
ps_front
dump 3-back
xdotool mousemove $TOOL click 1; sleep 2
dump 4-tool-click
switch
dump 5-tool-switched
import -window root -resize 25% "$OUT/5-tool-switched-25pct.png"
kill $(xdotool getwindowpid "$T"); w $RT/bin/wineserver -k
