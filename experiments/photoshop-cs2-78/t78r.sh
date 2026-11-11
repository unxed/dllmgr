#!/bin/sh
# t78r.sh OUT: #78 retest after the owner's v23 report (2026-11-11): click
# into a palette (History) and, separately, into the toolbox, then switch to
# a normal app (a big xterm) like Alt+Tab in Cinnamon, and dump the X
# stacking (stack.py, _NET_CLIENT_LIST_STACKING, xwininfo -tree), the Win32
# z-order with WS_EX_TOPMOST (PROBE = zlist78.exe), xprop of every
# Photoshop top-level and screenshots.
# 2026-11-11 evening: the owner sees the stuck palettes only with an image
# open (a separate framed document window, _NET_WM_WINDOW_TYPE_DIALOG), so
# SERVER0=/opt/wine-stable/bin/wineserver: start that (stock) wineserver
# for the prefix first, as the launch trampoline does (stock wine starts
# Photoshop.exe, its version.dll proxy relaunches through `dllmgr run`, and
# the private runtime connects to the server that already runs).
# a test image C:\t78.png is generated and opened, and the scenarios also
# click into the document and switch away while it is focused.
# BUSY=1 adds a last scenario like real work: hover every toolbox button
# long enough for its tooltip, paint strokes in the document, hover the
# palettes, open and close a menu, then switch; the Win32 exstyle of the
# palettes (0x88 = WS_EX_TOPMOST) is checked after each part.
# PAL=1 adds palette work before that switch, with the check after every
# step: History state clicks (after the strokes there are states), Layers
# rows, palette drags by the title strip, a resize from the bottom-right
# corner, tab clicks. Owner's live :0 (22:08): the History and Layers
# palettes had _NET_WM_STATE_ABOVE (History moved 2 px, Layers 40 px lower).
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
	# the stuck candidates: Photoshop windows above TERM, with their hints
	awk '/TERM"/ {exit} /photoshop/' "$OUT/$1-stack.txt" | sed 's/^/    ABOVE /'
	awk '/photoshop/ {if ($0 ~ /frame of/) {for (i=1; i<NF; i++) if ($i == "of") print $(i+1)} else print $1}' "$OUT/$1-stack.txt" |
	while read id; do
		echo "== $id"
		xprop -id "$id" WM_NAME WM_TRANSIENT_FOR _NET_WM_STATE _NET_WM_WINDOW_TYPE _MOTIF_WM_HINTS WM_CLIENT_LEADER WM_HINTS WM_NORMAL_HINTS
	done > "$OUT/$1-props.txt" 2>&1
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
[ -n "$SERVER0" ] && env WINEPREFIX="$WINEPREFIX" "$SERVER0" -p60
# which wineserver binary serves this prefix
sdir=/tmp/.wine-$(id -u)/server-$(stat -c '%d-%i' "$WINEPREFIX" | awk -F- '{printf "%x-%x", $1, $2}')
server_bin() { for p in $(pgrep -x wineserver); do [ "$(readlink /proc/$p/cwd)" = "$sdir" ] && readlink /proc/$p/exe; done; }
# our own test image (no ICC profile, so no profile-mismatch prompt)
[ -f "$WINEPREFIX/drive_c/t78.png" ] || convert -size 900x700 plasma:fractal -strip "$WINEPREFIX/drive_c/t78.png"
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} $EXTRA setsid $RT/bin/wine Photoshop.exe 'C:\t78.png' > "$OUT/wine.log" 2>&1 &)
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
for i in $(seq 15); do wmctrl -l | grep -q 't78.png' && break; sleep 2; done
DOC=$(xdotool search --name '^t78\.png' | head -1)
[ -n "$DOC" ] || echo "NO DOCUMENT WINDOW"
doc_click() {	# into the middle of the document's canvas
	eval "$(xdotool getwindowgeometry --shell "$DOC")"
	xdotool mousemove $((X + WIDTH / 2)) $((Y + HEIGHT / 2)) click 1; sleep 2
}
echo "server: $(server_bin)" | tee "$OUT/server.txt"
dump 0-before
import -window root -resize 25% "$OUT/0-before-25pct.png"
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
ps_front
if [ -n "$DOC" ]; then
	doc_click
	dump 6-doc-click
	xdotool mousemove $HIST click 1; sleep 2
	dump 7-doc-hist-click
	switch
	dump 8-doc-hist-switched
	import -window root -resize 25% "$OUT/8-doc-hist-switched-25pct.png"
	ps_front
	doc_click
	xdotool windowactivate --sync "$DOC"; sleep 2
	dump 9-doc-focused
	switch
	dump 10-doc-switched
	import -window root -resize 25% "$OUT/10-doc-switched-25pct.png"
fi
topm() {	# Photoshop palettes/toolbox that are WS_EX_TOPMOST right now
	echo "  $1: topmost: $(w WINEDEBUG=-all $RT/bin/wine "$PROBE" 2>/dev/null | grep 'vis=1' | grep -E 'PSFloatC|PSDocC|Photoshop ' | awk '$5 ~ /^ex=.......[89a-f]$/ {print $2 "/" $3}' | tr '\n' ' ')"
}
if [ -n "$DOC" ] && [ -n "$BUSY" ]; then
	ps_front
	for y in $(seq 200 50 1000); do for x in 50 110; do xdotool mousemove $x $y; sleep 1.6; done; done
	topm hover-toolbox
	xdotool mousemove 50 260 click 1; sleep 1; xdotool key b; sleep 1
	eval "$(xdotool getwindowgeometry --shell "$DOC")"
	for k in 1 2 3; do
		xdotool mousemove $((X + 100)) $((Y + 100 * k)) mousedown 1
		xdotool mousemove $((X + 300)) $((Y + 100 * k + 40)); sleep 0.3
		xdotool mousemove $((X + 500)) $((Y + 100 * k)) mouseup 1; sleep 1
	done
	topm paint
	for y in 200 330 470 600 740 870 1000 1200 1500; do xdotool mousemove 2780 $y; sleep 1.6; done
	topm hover-palettes
	if [ -n "$PAL" ]; then
		import -window root -crop 440x1560+2620+160 "$OUT/palettes-full.png"
		for y in 770 800 830 860 890 920; do xdotool mousemove 2780 $y click 1; sleep 1.5; topm "history-row-$y"; done
		for y in 1060 1100 1140; do xdotool mousemove 2800 $y click 1; sleep 1.5; topm "layers-row-$y"; done
		xdotool mousemove 2650 1100 click 1; sleep 1.5; topm layers-eye; xdotool mousemove 2650 1100 click 1; sleep 1.5
		drag() { xdotool mousemove $1 $2 mousedown 1; sleep 0.3; xdotool mousemove $(($1 + $3 / 2)) $(($2 + $4 / 2)); sleep 0.3; xdotool mousemove $(($1 + $3)) $(($2 + $4)); sleep 0.5; xdotool mouseup 1; sleep 1.5; }
		drag 2800 706 2 0; topm drag-history-title-2px
		drag 2800 706 -40 30; topm drag-history-title-far
		drag 2802 976 0 0; topm click-layers-title
		drag 3045 1660 0 -40; topm resize-layers
		for x in 2680 2780 2880; do xdotool mousemove $x 728 click 1; sleep 1.5; topm "history-tab-$x"; done
		for x in 2680 2780 2880; do xdotool mousemove $x 996 click 1; sleep 1.5; topm "layers-tab-$x"; done
		doc_click; topm doc-click
		dump 10b-pal
	fi
	xdotool mousemove 2780 800 click 1; sleep 1
	xdotool mousemove 60 40 click 1; sleep 2; xdotool key Escape; sleep 1
	topm menu
	doc_click
	dump 11-busy
	switch
	dump 12-busy-switched
	import -window root -resize 25% "$OUT/12-busy-switched-25pct.png"
	sleep 10; xdotool mousemove 1500 900; sleep 1; xdotool mousemove 2900 500; sleep 2
	dump 13-busy-later
fi
kill $(xdotool getwindowpid "$T"); w $RT/bin/wineserver -k
