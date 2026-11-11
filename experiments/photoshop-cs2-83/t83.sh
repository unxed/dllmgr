#!/bin/sh
# t83.sh OUT: #83 on the stand. Start Photoshop CS2 (activation + #84 box
# dismissed as in experiments/photoshop-cs2-78/wine-78/t78p-dismiss.sh),
# select the Brush tool (B), open the Opacity slider popup of the options bar
# and take screenshots. Run inside a stand session. TOOL: "X Y" of the Brush
# tool in the toolbox (default 105 428).
# Env: RT (runtime dir), WINEPREFIX, WDBG (WINEDEBUG while the popup opens,
# default -all), ARROW ("X Y" of the arrow next to Opacity; if unset, only
# the screenshot with the Brush tool is taken), POPDLL (optional extra
# WINEDLLOVERRIDES entry), EXTRA (extra "VAR=value ..." for Photoshop, e.g.
# DLLMGR27_DEBUG=1), PROBE (window-list probe exe, e.g. tests/wine zlist78.c,
# run while the popup is open), VIA_DLLMGR=1 (start with `dllmgr run
# photoshop-cs2` on a prefix where `dllmgr fix photoshop-cs2` was applied),
# CAP (tests/wine/screencap83.exe: screen-DC read of CAPRECT, default the
# popup rectangle "536 152 244 48", before and while the popup is open).
OUT=$1; mkdir -p "$OUT"
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
if [ -n "$VIA_DLLMGR" ]; then  # the owner's way: dllmgr fix applied, dllmgr run
	(env $EXTRA DLLMGR_VERBOSE=1 WINEDEBUG=${WDBG:--all} setsid dllmgr run photoshop-cs2 --prefix "$WINEPREFIX" > "$OUT/wine.log" 2>&1 &)
else
	(w DLLMGR27_NO_TRAMPOLINE=1 $EXTRA WINEDLLOVERRIDES="version=n,b${POPDLL:+;$POPDLL}" WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe > "$OUT/wine.log" 2>&1 &)
fi
for i in $(seq 60); do sleep 3; wmctrl -l 2>/dev/null | grep -q 'Activation' && break; done
sleep 3; xdotool mousemove 1788 1372 click 1; sleep 5; wmctrl -c 'Adobe Updater Preferences' 2>/dev/null; sleep 2
for i in $(seq 10); do [ "$(wmctrl -l | cut -c20- | grep -c '^Adobe Photoshop$')" -ge 2 ] && break; sleep 2; done
for id in $(wmctrl -lG | awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}'); do
	xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
done
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 2
xdotool mousemove ${TOOL:-105 428} sleep .5 mousedown 1 sleep .2 mouseup 1; sleep 2  # Brush tool in the toolbox
xdotool mousemove ${TOOL:-105 428} sleep .5 mousedown 1 sleep .2 mouseup 1; sleep 2
import -window root "$OUT/0-brush.png"
if [ -n "$ARROW" ]; then
	CR=${CAPRECT:-536 152 244 48}
	[ -n "$CAP" ] && { w WINEDEBUG=-all $RT/bin/wine "$CAP" $CR 'Z:'"$(echo "$OUT" | tr / '\\')"'\\cap-before.bmp'; import -window root "$OUT/x-before.png"; }
	echo "=== popup click $(date +%s.%N)" >> "$OUT/wine.log"
	xdotool mousemove $ARROW click 1; sleep 2
	import -window root "$OUT/1-popup.png"
	[ -n "$CAP" ] && w WINEDEBUG=-all $RT/bin/wine "$CAP" $CR 'Z:'"$(echo "$OUT" | tr / '\\')"'\\cap-open.bmp'
	[ -n "$PROBE" ] && w WINEDEBUG=-all $RT/bin/wine "$PROBE" > "$OUT/probe.txt" 2>/dev/null
	xwininfo -root -tree > "$OUT/tree.txt"
	sleep 1; import -window root "$OUT/2-popup-later.png"
	xdotool key Escape; sleep 1
	xdotool mousemove $ARROW click 1; sleep 2
	import -window root "$OUT/3-popup-again.png"
	xdotool key Escape; sleep 1
fi
w $RT/bin/wineserver -k
