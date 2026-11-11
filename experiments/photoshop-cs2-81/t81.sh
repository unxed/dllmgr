#!/bin/sh
# t81.sh OUT: #81 on the stand. Start Photoshop CS2 with C:\t46.png (as
# experiments/photoshop-cs2-80/t80.sh, F26 box dismissed), find the document
# window with tests/wine/kids81.c, press on its bottom-right corner and drag
# it in steps; after each step save xwininfo -root -tree, the probe's window
# list and a screenshot; then release and do the same once more.
# Env: RT (runtime dir), WINEPREFIX, PROBE (kids81.exe), WDBG (WINEDEBUG),
# EXTRA (env for wine), DX/DY (total drag, physical px), STEPS, HOLD (s per step).
OUT=$1; mkdir -p "$OUT"; DX=${DX:-480}; DY=${DY:-240}; STEPS=${STEPS:-4}; HOLD=${HOLD:-1}
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $EXTRA "$@"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
[ -n "$RELAY" ] && w WINEDEBUG=-all $RT/bin/wine reg add 'HKCU\Software\Wine\Debug' /v RelayInclude /d "$RELAY" /f >/dev/null 2>&1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
	xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
done
sleep 4
probe() { w WINEDEBUG=-all $RT/bin/wine "$PROBE" > "$OUT/kids-$1.txt" 2>/dev/null; xwininfo -root -tree > "$OUT/tree-$1.txt"; }
# the document first appears as a managed top-level window, then becomes an
# MDI child: wait for it among the children of the main window
for i in $(seq 15); do probe 0; grep -q ' @ ' "$OUT/kids-0.txt" && break; sleep 2; done
for i in $(seq 5); do wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2; done
probe 0
import -window root "$OUT/0-before.png"
# document: the MDI child whose title has " @ "
DOC=$(grep ' @ ' "$OUT/kids-0.txt" | head -1); echo "doc: $DOC" | tee "$OUT/doc.txt"
R=$(echo "$DOC" | sed -n 's/.* win=\([-0-9]*\),\([-0-9]*\)-\([-0-9]*\),\([-0-9]*\) .*/\3 \4/p')
set -- $R; [ -n "$1" ] || { w $RT/bin/wineserver -k; exit 1; }
SX=$(($1 - 4)); SY=$(($2 - 4))
xdotool mousemove $SX $SY; sleep 1; echo "press at $SX $SY, log bytes $(wc -c < "$OUT/wine.log")" >> "$OUT/steps.txt"
xdotool mousedown 1; sleep 1
XID=$(grep ' @ ' "$OUT/tree-0.txt" | head -1 | awk '{print $1}')
if [ -n "$FAST" ]; then
	# FAST=N: N small steps without pauses (pointer motion as from a hand),
	# the X position of the document's client window after each step
	# CAP=1: record the screen at 25 fps (half size) during the drag
	[ -n "$CAP" ] && { ffmpeg -v error -f x11grab -framerate 25 -video_size 3072x1728 -i "$DISPLAY" -vf scale=1536:-1 -c:v libx264 -preset ultrafast -crf 18 -y "$OUT/drag.mp4" < /dev/null & CAPPID=$!; sleep 1; }
	i=1; while [ $i -le $FAST ]; do
		xdotool mousemove $((SX + DX * i / FAST)) $((SY + DY * i / FAST)); sleep ${FASTDELAY:-0.03}
		echo "fast $i cursor $((SX + DX * i / FAST)) $((SY + DY * i / FAST)) $(xwininfo -id $XID | grep -E 'Absolute|Width|Height' | awk '{printf "%s ", $NF}')" >> "$OUT/steps.txt"
		[ $((i % (FAST / 8))) -eq 0 ] && import -window root "$OUT/1-fast-$i.png"
		i=$((i + 1))
	done
	[ -n "$CAP" ] && { sleep 1; kill -INT $CAPPID; wait $CAPPID; }
	STEPS=0
fi
i=1; while [ $i -le $STEPS ]; do
	xdotool mousemove $((SX + DX * i / STEPS)) $((SY + DY * i / STEPS)); sleep $HOLD
	echo "step $i cursor $((SX + DX * i / STEPS)) $((SY + DY * i / STEPS))" >> "$OUT/steps.txt"
	import -window root "$OUT/1-drag-$i.png"
	probe drag-$i
	i=$((i + 1))
done
echo "release, log bytes $(wc -c < "$OUT/wine.log")" >> "$OUT/steps.txt"; xdotool mouseup 1; sleep 0.3
import -window root "$OUT/2-release-0.3s.png"; sleep 2
import -window root "$OUT/2-after.png"
probe after
w $RT/bin/wineserver -k
