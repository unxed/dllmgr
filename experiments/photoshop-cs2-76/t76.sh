#!/bin/sh
# t76.sh OUT: #76 on the stand. Photoshop CS2 with a document; hit76.exe lists
# the windows of the classes the cursor hit test cares about and every screen
# point where that hit test would leave its window pointer unset (the crash
# at photoshop+0xb249ce), first idle, then with tool tips, the File menu, Page
# Setup and Print with Preview open.
# Env: RT (runtime dir), WINEPREFIX (a fresh copy of a never-started
# prefix-clean with C:\t46.png and the dllmgr-27 version.dll), PROBE
# (hit76.exe), STEP (grid step, default 8), SCEN=owner (zoom, screen modes,
# palette well, Tab instead of the print dialogs), SCEN=fake (synthetic
# trigger fake76.exe next to PROBE), SCEN=drag (palette drags). Run inside
# a stand session.
OUT=$1; mkdir -p "$OUT"; STEP=${STEP:-8}
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
probe() { w WINEDEBUG=-all $RT/bin/wine "$PROBE" $STEP > "$OUT/hit-$1.txt" 2>/dev/null; echo "$1: $(grep -c '^HAZARD' "$OUT/hit-$1.txt") hazard window(s); $(tail -1 "$OUT/hit-$1.txt")"; }
shot() { import -window root -resize 25% "$OUT/$1.png"; }
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cd "$PS" || exit 1
# structure watcher from before the splash on (every 50 ms)
(w WINEDEBUG=-all $RT/bin/wine "$PROBE" 0 struct ${STRUCT:-600} > "$OUT/hit-struct.txt" 2>/dev/null &)
sleep 2
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
# startup dialogs as in photoshop-cs2-68/v21-close.sh: Activation (trial
# continue button; a never-started prefix is needed, F25), the F26 "program
# error" box, Adobe Updater Preferences
quiet=0
for i in $(seq 80); do
	sleep 3; wmctrl -lG > "$OUT/wl.txt" 2>/dev/null; seen=0
	if grep -q 'Activation' "$OUT/wl.txt"; then
		seen=1; import -window root -resize 50% "$OUT/0-activation.png"; xdotool mousemove 1788 1372 click 1; sleep 3
	fi
	for id in $(awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}' "$OUT/wl.txt"); do
		seen=1; xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
	done
	if grep -q 'Adobe Updater Preferences' "$OUT/wl.txt"; then seen=1; wmctrl -c 'Adobe Updater Preferences'; sleep 2; fi
	if [ $seen = 0 ] && grep -q ' @ ' "$OUT/wl.txt"; then quiet=$((quiet + 1)); else quiet=0; fi
	[ $quiet -ge 3 ] && break
done
sleep 5
wmctrl -lG > "$OUT/windows.txt"
shot 0-idle; probe 0-idle
if [ "$SCEN" = drag ]; then
	# palette drags (the owner moved palettes and the toolbox that day, #78/#80):
	# History tab, Color palette title, toolbox title, slowly over the
	# document, the gray frame and the palette well, then dropped back
	F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
	drag() { # drag X Y NAME: press at X Y, wander, release at the start
		x0=$1 y0=$2 name=$3
		xdotool mousemove $x0 $y0; sleep 0.5; xdotool mousedown 1; sleep 0.5
		for p in "2400 700" "2000 700" "1600 600" "1200 500" "800 400" "600 300" "1648 532" "1748 144" "2000 140" "1648 900" "1000 1200"; do
			xdotool mousemove $p; sleep 0.6
		done
		shot "drag-$name"; xdotool mousemove $x0 $y0; sleep 0.5; xdotool mouseup 1; sleep 2
	}
	drag 2686 752 history; drag 2640 470 color; drag 60 196 toolbox
	xdotool mousemove 1648 532; sleep 10; probe drag-end; shot drag-end
	grep -a -E 'Unhandled|dllmgr76: (access|guard)' "$OUT/wine.log" | head
	w $RT/bin/wineserver -k; exit
fi
if [ "$SCEN" = fake ]; then
	# synthetic trigger (fake76.exe): a childless window of Photoshop's
	# document class under the cursor, then a popup owned by a childless
	# palette-class window; Photoshop foreground, cursor idle
	F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
	for v in "PSDocC 15" "PSFloatC 15 owned"; do
		xdotool mousemove 1648 900; sleep 1
		w WINEDEBUG=-all $RT/bin/wine "${PROBE%/*}/fake76.exe" $v &
		sleep 4; xdotool mousemove 1650 902; sleep 2; xdotool mousemove 1640 905; sleep 3
		shot "fake-${v%% *}"; wait
		pgrep -f 'Photoshop.exe' >/dev/null && echo "fake $v: Photoshop alive" || { echo "fake $v: Photoshop gone"; break; }
	done
	grep -a -E 'dllmgr76: (access|0x|hit)|Unhandled|^=>' "$OUT/wine.log" | head
	w $RT/bin/wineserver -k; exit
fi
# background watcher: hazards at the cursor and new hazard windows, 1/s
(w WINEDEBUG=-all $RT/bin/wine "$PROBE" 16 loop ${LOOP:-400} > "$OUT/hit-loop.txt" 2>/dev/null &)
# hover: sweep the cursor slowly over the whole screen, pausing for tool tips
for y in 150 300 500 700 900 1100 1300 1500; do
	for x in 40 300 600 900 1200 1500 1800 2100 2400 2700 2900 3040; do
		xdotool mousemove $x $y; sleep 0.7
	done
done
grep -q . "$OUT/hit-loop.txt" && echo "loop so far: $(grep -c . "$OUT/hit-loop.txt") line(s)"
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
# File menu open (by mouse: Ctrl accelerators are dead after F26)
xdotool mousemove 40 86 click 1; sleep 2; import -window root -resize 50% "$OUT/1-file-menu.png"; probe 1-file-menu; xdotool key Escape Escape; sleep 1
[ -n "$MENU_ONLY" ] && { w $RT/bin/wineserver -k; exit; }
menu() { # menu Y NAME: File menu item at full-res y
	F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
	xdotool mousemove 40 86 click 1; sleep 2; xdotool mousemove 120 $1 click 1; sleep 8
	shot "$2"; probe "$2"; wmctrl -lG > "$OUT/windows-$2.txt"
}
if [ "$SCEN" = owner ]; then
	# what the owner was doing around the crash (13:20 screenshot): zoom
	# tool, Alt+wheel zoom, cursor idle over the gray frame, screen modes,
	# palette well, Tab (hide palettes), document resize
	xdotool mousemove 106 754 click 1; sleep 2                 # Zoom tool
	xdotool mousemove 800 720; sleep 1
	for i in 1 2 3 4 5 6; do xdotool keydown alt click 4 keyup alt; sleep 0.4; done; sleep 3
	shot b1-zoomed-in; probe b1-zoomed-in
	for i in 1 2 3 4 5 6 7 8 9; do xdotool keydown alt click 5 keyup alt; sleep 0.4; done; sleep 3
	shot b2-zoomed-out; probe b2-zoomed-out
	xdotool mousemove 1648 532; sleep 15                        # the crash point, idle
	xdotool mousemove 800 720 click 1; sleep 3; xdotool mousemove 1648 532; sleep 5  # zoom-in click
	shot b3-click-zoom; probe b3-click-zoom
	for b in 1050 1200 1330; do xdotool mousemove $b 134 click 1; sleep 3; done      # Actual Pixels / Fit Screen / Print Size
	xdotool mousemove 1648 532; sleep 5; shot b4-buttons; probe b4-buttons
	xdotool mousemove 1748 144 click 1; sleep 3; shot b5-well; probe b5-well       # palette well: Brushes
	xdotool mousemove 1648 900; sleep 3; xdotool click 1; sleep 2
	for m in 78 110 46; do xdotool mousemove $m 972 click 1; sleep 4; xdotool mousemove 1648 532; sleep 4; probe b6-mode-$m; shot b6-mode-$m; done
	F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
	xdotool mousemove 1648 532 key Tab; sleep 4; probe b7-tab; shot b7-tab; xdotool key Tab; sleep 4
	D=$(xdotool search --name ' @ ' | head -1)
	[ -n "$D" ] && { xdotool windowsize $D 1600 1300; sleep 3; xdotool windowsize $D 900 700; sleep 3; }
	xdotool mousemove 1648 532; sleep 20; probe b8-end; shot b8-end
	w $RT/bin/wineserver -k; exit
fi
menu 932 2-page-setup
for x in 900 1300 1700; do xdotool mousemove $x 700; sleep 1; done
xdotool key Escape; sleep 3
menu 966 3-print-preview
for y in 300 600 900 1200; do for x in 600 1000 1400 1800 2200; do xdotool mousemove $x $y; sleep 0.7; done; done
xdotool key Escape; sleep 3
menu 1000 4-print
for x in 900 1300 1700; do xdotool mousemove $x 700; sleep 1; done
xdotool key Escape; sleep 3; xdotool key Escape; sleep 2
shot 5-after; probe 5-after
# idle a while longer with the cursor on the document title bar and the canvas
xdotool mousemove 400 100; sleep 20; xdotool mousemove 400 400; sleep 20
# close the document (File > Close), cursor parked where the document was
menu 366 6-close; xdotool mousemove 800 600; sleep 10; probe 7-closed
grep -E -i 'unhandled|page fault|dllmgr76' "$OUT/wine.log" | head -20
w $RT/bin/wineserver -k
