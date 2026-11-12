#!/bin/sh
# t83m.sh OUT: #83 follow-up (owner 2026-11-12: "moving leaves artifacts
# when the mouse pauses"). Start Photoshop CS2 as t83.sh does, select the
# Brush tool, then:
#  1. open the Opacity popup, press on its thumb, move left in quick small
#     steps (hand-like), pause, screenshots 0.2 s and 1.5 s into each pause,
#     release, screenshot;
#  2. drag the toolbox by its title strip the same way;
#  3. hover along the options bar in legs with pauses (tool tips);
#  4. new document: brush cursor over the canvas, drag the document window.
# Env: RT, WINEPREFIX, EXTRA (env for Photoshop, e.g. the dllmgr run
# settings), WDBG, THUMB ("X Y" of the slider thumb, default 759 174).
# Run inside a stand session.
OUT=$1; mkdir -p "$OUT"
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
(w DLLMGR27_NO_TRAMPOLINE=1 $EXTRA WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
	xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
done
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2
for k in 1 2; do xdotool mousemove 105 428 sleep .5 mousedown 1 sleep .2 mouseup 1; sleep 2; done  # Brush tool
import -window root "$OUT/0-brush.png"
# glide X0 Y0 DX DY N PREFIX: N legs of 10 quick 4-px moves each, a pause with
# two screenshots after every leg
glide() {
	x=$1; y=$2; leg=1
	while [ $leg -le $5 ]; do
		i=1; while [ $i -le 10 ]; do x=$((x + $3)); y=$((y + $4)); xdotool mousemove $x $y; sleep 0.02; i=$((i + 1)); done
		sleep 0.2; import -window root "$OUT/$6-$leg-a.png"
		sleep 1.3; import -window root "$OUT/$6-$leg-b.png"
		leg=$((leg + 1))
	done
}
# 1. slider
popup_up() { xwininfo -root -tree | grep -q '"photoshop.exe").*244x48+'; }
for t in 1 2 3; do  # the first click sometimes only shows the arrow's tool tip
	xdotool mousemove 757 137 sleep 0.3 click 1; sleep 2; popup_up && break
	xdotool mousemove 1500 900 sleep 0.5 click 1; sleep 1
done
popup_up && echo "popup open (try $t)" > "$OUT/popup.txt" || echo "popup NOT open" > "$OUT/popup.txt"
import -window root "$OUT/1-popup.png"
set -- ${THUMB:-759 174}
xdotool mousemove $1 $2; sleep 0.5; xdotool mousedown 1; sleep 0.3
glide $1 $2 -4 0 4 2-slider
xdotool mouseup 1; sleep 1.5
import -window root "$OUT/3-slider-released.png"
xdotool key Escape; sleep 1; xdotool mousemove 1500 900; sleep 1
import -window root "$OUT/4-slider-closed.png"
# 2. toolbox title strip
TB=""; for id in $(xdotool search --onlyvisible --classname photoshop.exe 2>/dev/null); do
	eval "$(xdotool getwindowgeometry --shell $id)"
	[ "$WIDTH" -lt 300 ] && [ "$HEIGHT" -gt 800 ] && TB="$X $Y $WIDTH $HEIGHT"
done
echo "toolbox: $TB" > "$OUT/toolbox.txt"
set -- $TB
if [ -n "$1" ]; then
	SX=$(($1 + $3 / 2)); SY=$(($2 + 8))
	xdotool mousemove $SX $SY; sleep 0.5; xdotool mousedown 1; sleep 0.3
	glide $SX $SY 8 4 4 5-toolbox
	xdotool mouseup 1; sleep 2
	import -window root "$OUT/6-toolbox-released.png"
fi
# 3. hover along the options bar with pauses (tool tips come up in the pauses)
xdotool mousemove 1500 900 click 1; sleep 1
xdotool mousemove 150 137; sleep 1
glide 150 137 10 0 8 7-hover
xdotool mousemove 1500 900; sleep 1.5
import -window root "$OUT/8-hover-done.png"
# 4. new document (Ctrl+N, Enter), brush cursor over the canvas with pauses,
#    then drag the document window by its title bar with pauses
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
xdotool key ctrl+n; sleep 3
wmctrl -l | grep -q ' New$' || { xdotool mousemove 40 86 click 1; sleep 1.5; xdotool key n; sleep 3; }  # File > New
wmctrl -l | cut -c20- > "$OUT/windows-new.txt"
xdotool key Return; sleep 4
import -window root "$OUT/9-doc.png"
D=$(xdotool search --onlyvisible --name '@ ' | head -1)
if [ -n "$D" ]; then
	eval "$(xdotool getwindowgeometry --shell $D)"; echo "doc $D ${WIDTH}x${HEIGHT}+$X+$Y" > "$OUT/doc.txt"
	CX=$((X + WIDTH / 4)); CY=$((Y + HEIGHT / 3))
	xdotool mousemove $CX $CY; sleep 1
	glide $CX $CY 6 3 4 10-canvas
	xdotool mousemove $((X + WIDTH / 2)) $((Y - 20)); sleep 0.5; xdotool mousedown 1; sleep 0.3
	glide $((X + WIDTH / 2)) $((Y - 20)) 8 4 4 11-docdrag
	xdotool mouseup 1; sleep 2
	import -window root "$OUT/12-docdrag-released.png"
fi
w $RT/bin/wineserver -k
