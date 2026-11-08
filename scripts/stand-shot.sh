#!/bin/sh
# Screenshot helpers for the headless sandbox stand (docs/sandbox-stand.md).
# Cheap on tokens: list windows as text first, look at images only when needed,
# and prefer the client area of one window at reduced scale.
#
#   stand-shot.sh list                      visible windows: id "title" WxH+X+Y
#   stand-shot.sh wait REGEX [SECONDS]      wait (default 90 s) for a visible title
#   stand-shot.sh win NAME REGEX [SCALE]    client area of last matching window
#   stand-shot.sh root NAME [SCALE]         whole screen
#
# Images go to $SHOT_DIR (default /home/claude/work/shots) as NAME.png (full)
# and NAME-s.png (SCALE, default 50%). Coordinates for
# `xdotool mousemove --window ID X Y` are full-size client-area pixels, i.e.
# coordinates in the 50% image times 2.
set -eu
export DISPLAY=${DISPLAY:-:93}
SHOT_DIR=${SHOT_DIR:-/home/claude/work/shots}
mkdir -p "$SHOT_DIR"

list() {
	xdotool search --onlyvisible --name . 2>/dev/null | while read -r w; do
		eval "$(xdotool getwindowgeometry --shell "$w")"
		g="${WIDTH}x${HEIGHT}+${X}+${Y}"
		echo "$w \"$(xdotool getwindowname "$w")\" $g"
	done | grep -v -e '"mutter guard window"' -e '"muffin"' || true
}

case "${1:-}" in
list) list ;;
wait)
	t=0; max=${3:-90}
	until xdotool search --onlyvisible --name "$2" >/dev/null 2>&1; do
		[ $t -ge "$max" ] && { echo "timeout ${max}s waiting for /$2/"; list; exit 1; }
		sleep 1; t=$((t + 1))
	done
	echo "found /$2/ after ${t}s"; list ;;
win)
	w=$(xdotool search --onlyvisible --name "$3" | tail -1)
	[ -n "$w" ] || { echo "no window /$3/"; list; exit 1; }
	import -window "$w" "$SHOT_DIR/$2.png"
	convert "$SHOT_DIR/$2.png" -resize "${4:-50%}" "$SHOT_DIR/$2-s.png"
	echo "$w \"$(xdotool getwindowname "$w")\" $(identify -format %wx%h "$SHOT_DIR/$2.png") -> $SHOT_DIR/$2-s.png" ;;
root)
	import -window root "$SHOT_DIR/$2.png"
	convert "$SHOT_DIR/$2.png" -trim -resize "${3:-33%}" "$SHOT_DIR/$2-s.png"
	echo "$SHOT_DIR/$2-s.png" ;;
*) sed -n '2,15p' "$0"; exit 2 ;;
esac
