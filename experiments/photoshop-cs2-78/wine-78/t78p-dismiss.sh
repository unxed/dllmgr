#!/bin/sh
# t78p.sh OUT: #78/#82 on the stand, the same steps as the Windows probe
# (tests/wine/ps35-palette.ps1): Photoshop with a document, click into the
# History palette, foreground/active/focus (tests/wine/fgprobe78.c), switch to
# a big xclock (#78), back, click History again, Alt+F4 (#82).
# Env: RT (runtime dir), WINEPREFIX, PROBE (fgprobe78.exe), WDBG (WINEDEBUG),
# HIST ("X Y" of a History row), DISMISS=1 closes the F26 "program error"
# box first. Run inside a stand session.
OUT=$1; mkdir -p "$OUT"; HIST=${HIST:-2780 800}
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
probe() { w WINEDEBUG=-all $RT/bin/wine "$PROBE" Photoshop list > "$OUT/probe-$1.txt" 2>/dev/null; head -1 "$OUT/probe-$1.txt" | sed "s/^/$1: /"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
if [ -n "$DISMISS" ]; then
	# F26: close the "program error" box (a second top-level "Adobe Photoshop"
	# window, the smaller one) with Enter, then expect one such window.
	for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
	for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
		xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
	done
	n=$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$'); echo "dismiss: $n 'Adobe Photoshop' window(s) left"
	import -window root "$OUT/0-dismissed.png"
fi
(xclock -geometry 3000x1650+30+30 &); sleep 2
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2
probe before
xdotool mousemove $HIST click 1; sleep 2
probe after-click
import -window root "$OUT/1-after-click.png"
wmctrl -a xclock; sleep 3
probe after-switch
import -window root "$OUT/2-after-switch.png"
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2
xdotool mousemove $HIST click 1; sleep 2
xdotool key alt+F4; sleep 3
probe after-altf4
wmctrl -l | cut -c20- > "$OUT/windows-after-altf4.txt"
import -window root "$OUT/3-after-altf4.png"
pkill xclock; w $RT/bin/wineserver -k
