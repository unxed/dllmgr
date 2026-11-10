#!/bin/sh
# t40c.sh OUT IMAGE: timeline of `dllmgr run faststone -- IMAGE` every 50 ms:
# FastStone windows mapped, which X window has the input focus (and whose it
# is), and the active window the WM reports. STOCK=PATH/FSViewer.exe: stock Wine. Shows the gap between "the window
# is on screen" and "keys reach it". Run inside a stand session.
OUT=$1; IMG=$2; mkdir -p "$OUT"
# The previous focus owner, like the owner's terminal: an xterm-less stand has
# none, so give the focus to a small X client first.
xclock -geometry 200x200+10+10 & clk=$!; sleep 1
xdotool search --class xclock | head -1 | xargs -r xdotool windowactivate --sync
t0=$(date +%s%N)
if [ -n "${STOCK:-}" ]; then  # stock /opt/wine-stable, the proxy and private DLLs off
	env DLLMGR27_OFF=1 WINEDLLOVERRIDES=msimg32=b /opt/wine-stable/bin/wine "$STOCK" "$(winepath -w "$IMG" 2>/dev/null || echo "$IMG")" > "$OUT/run.log" 2>&1 &
else
	dllmgr run faststone -- "$IMG" > "$OUT/run.log" 2>&1 &
fi
: > "$OUT/timeline.txt"
for _ in $(seq 160); do
	t=$(( ($(date +%s%N) - t0) / 1000000 ))
	fs=$(xdotool search --onlyvisible --class fsviewer.exe 2>/dev/null | tr '\n' ' ')
	f=$(xdotool getwindowfocus 2>/dev/null)
	fc=$(xprop -id "$f" WM_CLASS 2>/dev/null | cut -d'"' -f2)
	a=$(xprop -root _NET_ACTIVE_WINDOW | sed 's/.*# //')
	echo "$t ms fs=[$fs] focus=$f($fc) active=$a" >> "$OUT/timeline.txt"
	sleep .05
done
# collapse repeats: print only the lines where something changed
awk '{k=$0; sub(/^[0-9]+ ms /,"",k); if (k!=p) print; p=k}' "$OUT/timeline.txt" | tee "$OUT/changes.txt"
kill $clk; pkill -f '[F]SViewer.exe'; sleep 2
