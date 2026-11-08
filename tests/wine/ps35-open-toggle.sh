#!/bin/sh
# #35 (Wine 34134): Photoshop CS2 File > Open, OS dialog -> "Use Adobe Dialog"
# -> "Use OS Dialog"; prints the X window id and size of the "Open" window at
# each stage. Run inside a stand session (STAND_WM=metacity, 192 DPI prefix
# with CS2 installed by scripts/sandbox-install-cs2.sh):
#   sh scripts/sandbox-stand.sh session sh tests/wine/ps35-open-toggle.sh WINE_BIN LOG
# WINEDEBUG is passed through (e.g. +win) and the wine log goes to LOG.
# Click positions are client pixels at 192 DPI from the sandbox screenshots.
set -eu
wine=$1 log=$2
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
"$wine" "$exe" >"$log" 2>&1 &
t=0
until xdotool search --onlyvisible --class photoshop.exe >/dev/null 2>&1 && [ $t -ge 35 ]; do
	sleep 1; t=$((t + 1)); [ $t -lt 180 ] || { echo "photoshop did not start"; exit 1; }
done
open_size() {
	w=$(xdotool search --onlyvisible --name '^Open$' | tail -1)
	eval "$(xdotool getwindowgeometry --shell "$w")"
	echo "$1 xid=$w size=${WIDTH}x$HEIGHT"
}
xdotool mousemove 34 82 click 1; sleep 1.5; xdotool key o; sleep 4
open_size os-before
w=$(xdotool search --onlyvisible --name '^Open$' | tail -1)
echo "MARK adobe-click" >>"$log"
xdotool windowactivate --sync "$w" mousemove --window "$w" 136 1086 click 1; sleep 3
open_size adobe
w=$(xdotool search --onlyvisible --name '^Open$' | tail -1)
echo "MARK os-click" >>"$log"
xdotool windowactivate --sync "$w" mousemove --window "$w" 140 1088 click 1; sleep 3
open_size os-after
"$(dirname "$wine")/wineserver" -k 2>/dev/null || :
