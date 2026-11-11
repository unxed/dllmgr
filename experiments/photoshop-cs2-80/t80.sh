#!/bin/sh
# t80.sh OUT: #80 on the stand. Start Photoshop CS2 with C:\t46.png (as
# experiments/photoshop-cs2-78/wine-78/t78p-dismiss.sh, F26 box dismissed),
# find the toolbox (narrow tall photoshop.exe X window), drag it by its title
# strip with xdotool in steps, screenshot mid-drag and after the release.
# Env: RT (runtime dir), WINEPREFIX, WDBG (WINEDEBUG), EXTRA (env for wine),
# DX/DY (total drag), STEPS. Run inside a stand session.
OUT=$1; mkdir -p "$OUT"; DX=${DX:-600}; DY=${DY:-300}; STEPS=${STEPS:-6}
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver $EXTRA "$@"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
# RELAY="user32.GetDC;gdi32.PatBlt;...": relay only these (Wine's own DLLs)
[ -n "$RELAY" ] && w WINEDEBUG=-all $RT/bin/wine reg add 'HKCU\Software\Wine\Debug' /v RelayInclude /d "$RELAY" /f >/dev/null 2>&1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
	xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
done
sleep 3
# toolbox: the visible photoshop.exe window narrower than 300 and taller than 800
TB=""; for id in $(xdotool search --onlyvisible --classname photoshop.exe 2>/dev/null); do
	eval "$(xdotool getwindowgeometry --shell $id)"
	echo "win $id ${WIDTH}x${HEIGHT}+$X+$Y" >> "$OUT/windows.txt"
	[ "$WIDTH" -lt 300 ] && [ "$HEIGHT" -gt 800 ] && TB="$X $Y $WIDTH $HEIGHT"
done
echo "toolbox: $TB" | tee "$OUT/toolbox.txt"
import -window root "$OUT/0-before.png"
set -- $TB; [ -n "$1" ] || { w $RT/bin/wineserver -k; exit 1; }
SX=$(($1 + $3 / 2)); SY=$(($2 + 8))
xdotool mousemove $SX $SY; sleep 1; echo "log bytes before mousedown $(wc -c < "$OUT/wine.log")" >> "$OUT/steps.txt"; xdotool mousedown 1; sleep 1
i=1; while [ $i -le $STEPS ]; do
	xdotool mousemove $((SX + DX * i / STEPS)) $((SY + DY * i / STEPS)); sleep 1
	echo "step $i cursor $((SX + DX * i / STEPS)) $((SY + DY * i / STEPS))" >> "$OUT/steps.txt"
	import -window root "$OUT/1-drag-$i.png"
	i=$((i + 1))
done
echo "log bytes before mouseup $(wc -c < "$OUT/wine.log")" >> "$OUT/steps.txt"; xdotool mouseup 1; sleep 2
import -window root "$OUT/2-after.png"
for id in $(xdotool search --onlyvisible --classname photoshop.exe 2>/dev/null); do
	eval "$(xdotool getwindowgeometry --shell $id)"; echo "win $id ${WIDTH}x${HEIGHT}+$X+$Y" >> "$OUT/windows-after.txt"
done
w $RT/bin/wineserver -k
