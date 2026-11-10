#!/bin/sh
# fsru.sh NAME LAYOUT GROUP: FastStone 8.5 shortcuts with an XKB layout.
# Run inside a stand session (SD=:133 SDIR=$B/sub4 $B/run.sh sh fsru.sh ...).
#   LAYOUT: setxkbmap layout list (us,ru or ru,us)
#   GROUP:  XKB group locked before FastStone starts (0 = first layout);
#           LATE=1 locks it only after FastStone is up (switch while running)
# Keys go through xkey.py as physical keycodes (XTest), mouse clicks through
# xdotool; dialogs are closed with wmctrl -c (WM_DELETE_WINDOW), so only the
# tested key travels through the keyboard. Results: $OUT/NAME/results.tsv
# (scenario, context, key, result, detail). WDBG=+key,+keyboard for traces.
set -u
NAME=$1; LAYOUT=$2; GROUP=$3
H=$(cd "$(dirname "$0")" && pwd)
. "$H/env.sh"
OUT=${OUT:-$B/fsru/out}/$NAME; T=$B/fsru/t; I=$T/imgs
mkdir -p "$OUT"; rm -f "$OUT"/*; rm -f "$T"/*.jpg; sh "$H/mkimg.sh" "$I"
R=$OUT/results.tsv; : > "$R"
K() { python3 "$H/xkey.py" "$@"; }
rec() { printf '%s\t%s\t%s\t%s\t%s\n' "$NAME" "$1" "$2" "$3" "$4" >> "$R"; echo "$1 $2: $3 ($4)"; }
has() { wmctrl -l | cut -d' ' -f5- | grep -qF "$1"; }
waitwin() { n=0; while [ $n -lt $(( ${2:-6} * 10 )) ]; do has "$1" && return 0; sleep .1; n=$((n+1)); done; return 1; }
gone() { n=0; while [ $n -lt 40 ]; do has "$1" || return 0; sleep .1; n=$((n+1)); done; return 1; }
close() { wmctrl -c "$1"; gone "$1"; sleep .5; }
title() { wmctrl -l | grep 'FastStone Image Viewer' | cut -d' ' -f5- | sed 's/  -  FastStone.*//'; }
full() { wmctrl -lG | awk '$5 == 3072 && $6 == 1728' | grep -q .; }
ovl() { import -window root -crop 1200x40+0+0 +repage "$OUT/$1.png"; }
same() { [ "$(compare -metric AE "$OUT/$1.png" "$OUT/$2.png" null: 2>&1)" = 0 ]; }
shot() { import -window root -resize 50% "$OUT/$1.png"; }
dialog() {  # dialog CONTEXT KEY TITLE [WAIT]: KEY must open a window titled TITLE
	K "$2"
	if waitwin "$3" "${4:-6}"; then rec "$1" "$2" works "opens '$3'"; shot "$1-$2"; close "$3"
	else rec "$1" "$2" FAILS "no '$3' window"; shot "$1-$2"; fi
}
cell() { echo "$((1226 + 276 * $1)) 524"; }  # thumbnail N (0-based), 192 DPI

setxkbmap -layout "$LAYOUT"
[ "${LATE:-0}" = 1 ] || K -g "$GROUP"
echo "xkb: $(setxkbmap -query | grep layout) $(python3 "$H/../photoshop-cs2-49/xkbgroup.py")" > "$OUT/xkb.txt"
fs_start "$OUT/wine.log" 'Z:\home\unxed\.cache\dllmgr-agent\cc-rcnb-52ab\fsru\t'
waitwin 'FastStone Image Viewer' 60 || { echo "FastStone did not start"; exit 1; }
sleep 6
xdotool mousemove $(cell 0) click --repeat 2 1; sleep 3   # open the imgs folder ($T has only it)
[ "${LATE:-0}" = 1 ] && K -g "$GROUP"
echo "at keys: $(python3 "$H/../photoshop-cs2-49/xkbgroup.py")" >> "$OUT/xkb.txt"

# --- browser ---------------------------------------------------------------
xdotool mousemove $(cell 0) click 1; sleep 1
import -window root -crop 420x40+1600+1540 +repage "$OUT/sel0.png"
K ctrl+38; sleep 1
import -window root -crop 420x40+1600+1540 +repage "$OUT/sel1.png"
if same sel0 sel1; then rec browser ctrl+38 FAILS "Ctrl+A: selection count unchanged"
else rec browser ctrl+38 works "Ctrl+A: status bar 'Выбрано' 1 -> 3"; fi
K ctrl+54; sleep 1                                  # Ctrl+C: files to clipboard
xdotool mousemove 1114 326 click 1; sleep 2         # toolbar "back": $T
xdotool mousemove 1900 900 click 1; sleep .5
K ctrl+55; sleep 3                                  # Ctrl+V: paste the files
n=$(ls "$T"/*.jpg 2>/dev/null | wc -l)
if [ "$n" -gt 0 ]; then rec browser ctrl+54/ctrl+55 works "Ctrl+C, Ctrl+V: $n file(s) pasted into the parent"
else rec browser ctrl+54/ctrl+55 FAILS "Ctrl+C, Ctrl+V: nothing pasted"; fi
xdotool mousemove 1168 326 click 1; sleep 2         # toolbar "forward": $I

xdotool mousemove $(cell 1) click 1; sleep 1        # b.jpg
K 68
if waitwin 'Переименование' 5; then
	rec browser F2 works "opens 'Переименование'"
	K 42 43 56 40 28 57 36; sleep 2                 # physical keys g h b d t n, Enter
	new=$(cd "$I" && ls | grep -v '^[ac]\.jpg$' | tr '\n' ' ')
	rec rename-text "g,h,b,d,t,n" typed "file renamed to: $new"
	has 'Переименование' && close 'Переименование'
else rec browser F2 FAILS "no rename dialog"; fi

xdotool mousemove $(cell 0) click 1; sleep 1        # a.jpg
dialog browser ctrl+27 'Изменение размера'
xdotool mousemove $(cell 0) click 1; sleep 1
dialog browser 53 'Обрезка'

# --- fullscreen viewer -----------------------------------------------------
xdotool mousemove $(cell 0) click 1; sleep 1
K 36
n=0; while [ $n -lt 80 ] && ! full; do sleep .1; n=$((n+1)); done
if ! full; then rec browser Return FAILS "no fullscreen viewer"; shot browser-Return
else
	rec browser Return works "fullscreen viewer opens"
	waitwin 'Информация' 3 && close 'Информация'    # first fullscreen use hint
	xdotool mousemove 1536 1300; sleep 1
	t0=$(title); K 117; sleep 1.5; t1=$(title)
	[ "$t0" != "$t1" ] && rec viewer Next works "PgDn: $t0 -> $t1" || rec viewer Next FAILS "PgDn: title stays $t0"
	K 112; sleep 1.5; t2=$(title)
	[ "$t2" = "$t0" ] && rec viewer Prior works "PgUp: $t1 -> $t2" || rec viewer Prior FAILS "PgUp: title $t2"
	for k in 86 82 shift+21 20; do                  # KP_Add, KP_Subtract, '+', '-'
		ovl "z0-$k"; K $k; sleep 1.2; ovl "z1-$k"
		same "z0-$k" "z1-$k" && rec viewer "$k" FAILS "zoom % unchanged" || rec viewer "$k" works "zoom % changes"
	done
	dialog viewer 39 'Слайдшоу'
	dialog viewer ctrl+27 'Изменение размера'
	P='640x1000+2432+340'                           # I: properties panel at the right edge
	import -window root -crop $P +repage "$OUT/i0.png"; K 31; sleep 2; import -window root -crop $P +repage "$OUT/i1.png"
	same i0 i1 && rec viewer 31 FAILS "I: no properties panel" || rec viewer 31 works "I: properties panel shown"
	K 31; sleep 1.5
	dialog viewer 53 'Обрезка'
	dialog viewer 40 'Рисование' 12
	K 26                                             # E: first external program
	if waitwin 'Информация' 5; then rec viewer 26 works "E: 'no external program defined' notice"; close 'Информация'
		waitwin 'Настройки' 5 && close 'Настройки'
	else rec viewer 26 FAILS "E: nothing"; shot viewer-26; fi
	ovl r0; K 27; sleep 1.5; ovl r1                  # R rotates right: 1200 x 800 -> 800 x 1200
	same r0 r1 && rec viewer 27 FAILS "R: no rotation" || rec viewer 27 works "R: rotated"
	K 46; sleep 1.5; ovl r2                         # L rotates back
	same r1 r2 && rec viewer 46 FAILS "L: no rotation" || rec viewer 46 works "L: rotated back"
	K 9; sleep 2                                     # Esc: leave the viewer (asks to save the rotation)
	if waitwin 'Подтвердите' 3; then
		eval "$(xdotool search --name '^Подтвердите$' getwindowgeometry --shell | grep -E '^(X|Y|WIDTH|HEIGHT)=')"
		xdotool mousemove $((X + WIDTH / 2)) $((Y + HEIGHT * 3 / 4)) click 1; sleep 2   # "Нет"
	fi
	full && rec viewer Escape FAILS "viewer still open" || rec viewer Escape works "back to the browser"
fi
shot final
ls "$I" > "$OUT/files.txt"
fs_kill
