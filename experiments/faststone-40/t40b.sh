#!/bin/sh
# t40b.sh OUT IMAGE [DELAYS]: the owner's path (`dllmgr run faststone -- IMAGE`),
# Esc at each delay (seconds after the FastStone window is mapped); records
# when the window gets the X focus and whether Esc was answered (confirmation
# dialog or exit). Run inside a stand session with the recipe installed.
OUT=$1; IMG=$2; DELAYS=${3:-0.5 1 2 3 5}; mkdir -p "$OUT"
now() { date +%s.%N | cut -c1-14; }
for d in $DELAYS; do
	o=$OUT/d$d; mkdir -p "$o"
	t0=$(now)
	dllmgr run faststone -- "$IMG" > "$o/run.log" 2>&1 &
	w=''
	while [ -z "$w" ]; do w=$(xdotool search --onlyvisible --class fsviewer.exe 2>/dev/null | head -1); sleep .05; done
	tm=$(now)
	sleep "$d"
	f=$(xdotool getwindowfocus 2>/dev/null); fn=$(xprop -id "$f" WM_NAME 2>/dev/null | cut -d'"' -f2)
	import -window root "$o/1-before-esc.png"
	wmctrl -l | sort > "$o/win-before.txt"
	te=$(now); xdotool key Escape
	ans=no
	for _ in $(seq 60); do
		sleep .1
		wmctrl -l | sort > "$o/win-after.txt"
		if comm -13 "$o/win-before.txt" "$o/win-after.txt" | grep -q .; then ans="dialog($(comm -13 "$o/win-before.txt" "$o/win-after.txt" | cut -c20- | head -1))"; break; fi
		pgrep -f "[F]SViewer.exe" >/dev/null || { ans=exit; break; }
	done
	ta=$(now)
	import -window root "$o/2-after-esc.png"
	echo "delay=$d mapped=$(echo "$tm - $t0" | bc)s focus_at_esc=$f ($fn) answer=$ans after=$(echo "$ta - $te" | bc)s" | tee -a "$OUT/summary.txt"
	xdotool getwindowfocus >/dev/null
	/opt/wine-stable/bin/wineserver -k 2>/dev/null; pkill -f "[F]SViewer.exe"; sleep 2
done
