#!/bin/sh
# v21-close.sh OUT SCEN: #68 recheck on a runtime (RT=...), inside a stand
# session. Starts Photoshop CS2 on a fresh copy of PFX (cp -a, deleted at the
# end) with C:\t46.png, dismisses the startup dialogs, Type tool, clicks into
# the document, types "abc", then closes it by SCEN:
#   ctrlw     Ctrl+W (dead on this stand: Photoshop's Ctrl accelerators do
#             nothing after the F26 startup "program error"; Notepad Ctrl+O works)
#   menu      File > Close by mouse (same close command as Ctrl+W)
#   altf4     Alt+F4 (Muffin's keybinding -> WM_DELETE_WINDOW to the focused window)
#   closebtn  click on the document frame's close button (CLOSE="X Y" overrides)
# XCLOCK=1 first clicks into a big xclock and comes back by _NET_ACTIVE_WINDOW
# on the main frame (like a taskbar click); XCLOCK=click also clicks into the
# document's text after that.
# then records wmctrl, _NET_WM_USER_TIME, _NET_WM_STATE, the root stacking and
# the active window, and prints a verdict: the confirmation must be above the
# document (and xclock) and _NET_ACTIVE_WINDOW. WDBG=... sets WINEDEBUG.
OUT=$1; SCEN=$2; mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
B=${B:-/home/unxed/.cache/dllmgr-agent/cc-rcnb-52ab}
PFX=${PFX:-$B/ps/prefix-clean}  # prefix-auto's trial is over (blocks at "Activation Required")
export WINEPREFIX=$B/sub3/pfx-$SCEN LC_ALL=C.UTF-8
rm -rf "$WINEPREFIX"; cp -a "$PFX" "$WINEPREFIX" || exit 1
[ -e "$WINEPREFIX/drive_c/t46.png" ] || cp "$B/ps/prefix-auto/drive_c/t46.png" "$WINEPREFIX/drive_c/"
setxkbmap -layout us,ru 2>/dev/null
w() { env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver "$@"; }
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
(w DLLMGR27_NO_TRAMPOLINE=1 WINEDLLOVERRIDES=version=n,b WINEDEBUG=${WDBG:--all} setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > "$OUT/wine.log" 2>&1 &)
# startup dialogs, in whatever order they come: "Activation" (trial; click
# its continue button), the F26 "program error" box (a second, smaller
# top-level "Adobe Photoshop": activate, Return), "Adobe Updater Preferences"
# (close). Done when the document is up and none of them was seen for 3 polls.
quiet=0
for i in $(seq 80); do
	sleep 3; wmctrl -lG > "$OUT/wl.txt" 2>/dev/null; seen=0
	if grep -q 'Activation' "$OUT/wl.txt"; then
		seen=1; import -window root "$OUT/0-activation.png"; xdotool mousemove 1788 1372 click 1; sleep 3
	fi
	for id in $(awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}' "$OUT/wl.txt"); do
		seen=1; import -window root "$OUT/0-errbox.png"
		xdotool windowactivate --sync $((id)); sleep 1; xdotool key Return; sleep 2
	done
	if grep -q 'Adobe Updater Preferences' "$OUT/wl.txt"; then seen=1; wmctrl -c 'Adobe Updater Preferences'; sleep 2; fi
	if [ $seen = 0 ] && grep -q ' @ ' "$OUT/wl.txt"; then quiet=$((quiet + 1)); else quiet=0; fi
	[ $quiet -ge 3 ] && break
done
sleep 3
wmctrl -lG > "$OUT/w0.txt"
import -window root "$OUT/1-ready.png"
F=$(xdotool search --name '^Adobe Photoshop$' | head -1)
# document window: title with " @ "
set -- $(awk '/ @ /{print $3, $4, $5, $6; exit}' "$OUT/w0.txt")
DX=$1 DY=$2 DW=$3 DH=$4
[ -n "$DX" ] || { echo "no document window"; cat "$OUT/w0.txt"; w $RT/bin/wineserver -k; rm -rf "$WINEPREFIX"; exit 1; }
CX=$((DX + DW / 2)) CY=$((DY + DH / 2))
xdotool windowactivate --sync "$F"; sleep 1
# Type tool by its toolbox button: the T key is lost right after the F26 box
xdotool mousemove 108 608 click 1; sleep 2
xdotool mousemove $CX $CY; sleep 1; xdotool mousedown 1; sleep 0.3; xdotool mouseup 1; sleep 4
xdotool type --delay 80 abc; sleep 2
import -window root "$OUT/2-typing.png"
if [ -n "$XCLOCK" ]; then
	# away to another app (click into a big xclock) and back like a taskbar
	# click (_NET_ACTIVE_WINDOW on the main frame), then a click into the
	# document's text so the type edit is live again
	xclock -geometry 3000x1650+30+30 & XPID=$!
	sleep 3; xdotool mousemove 1500 855; sleep 1; xdotool click 1; sleep 3
	xprop -root _NET_ACTIVE_WINDOW > "$OUT/active-in-xclock.txt"
	import -window root "$OUT/3-in-xclock.png"
	xdotool windowactivate --sync "$F"; sleep 3
	xprop -root _NET_ACTIVE_WINDOW _NET_CLIENT_LIST_STACKING > "$OUT/back.txt"
	import -window root "$OUT/3-back.png"
	[ "$XCLOCK" = click ] && { xdotool mousemove $CX $CY; sleep 1; xdotool click 1; sleep 2; }
fi
DOC=$(awk '/ @ /{print $1; exit}' "$OUT/w0.txt")
case $SCEN in
ctrlw) xdotool key ctrl+w ;;
menu) xdotool mousemove 40 85 click 1; sleep 2; xdotool mousemove 75 366 click 1 ;;   # File > Close
altf4) xdotool key alt+F4 ;;
closebtn)
	# CLOSE="X Y", else the document frame's close button (Muffin decoration;
	# wmctrl reports the client area)
	set -- ${CLOSE:-$((DX + DW - 27)) $((DY - 67))}
	xdotool mousemove $1 $2; sleep 1; xdotool click 1 ;;
esac
sleep 6
wmctrl -lG > "$OUT/w1.txt"
import -window root "$OUT/4-close.png"
{
	echo "== wmctrl -lG"; cat "$OUT/w1.txt"
	echo "== root"; xprop -root _NET_ACTIVE_WINDOW _NET_CLIENT_LIST_STACKING
	echo "== focus: $(xdotool getwindowfocus)"
	for id in $(awk '{print $1}' "$OUT/w1.txt"); do
		echo "== $id $(xprop -id $id WM_NAME | cut -d= -f2)"
		xprop -id $id _NET_WM_USER_TIME _NET_WM_STATE WM_TRANSIENT_FOR _NET_WM_WINDOW_TYPE
	done
} > "$OUT/props.txt" 2>&1
# verdict: dialog = the newest small top-level "Adobe Photoshop" (not the frame)
DLG=$(awk '{t=$8; for (i=9; i<=NF; i++) t=t" "$i} t=="Adobe Photoshop" && $5<1500 {print $1}' "$OUT/w1.txt" | tail -1)
ACT=$(xprop -root _NET_ACTIVE_WINDOW | sed 's/.*# //; s/,.*//')
# stacking index (bottom = 1) of the dialog vs the document and xclock; the
# toolbox palette is TOPMOST and always last (#78 area), so it is not compared
ST=$(xprop -root _NET_CLIENT_LIST_STACKING | sed 's/.*# //' | tr ',' '\n' | tr -d ' ')
idx() { n=0; for x in $ST; do n=$((n + 1)); [ $((x)) = $(($1)) ] && { echo $n; return; }; done; echo 0; }
XC=$(xdotool search --class xclock 2>/dev/null | head -1)
above() { [ -z "$2" ] && { echo n/a; return; }; [ $(idx $1) -gt $(idx $2) ] && echo yes || echo NO; }
UT=$(xprop -id "${DLG:-0}" _NET_WM_USER_TIME 2>/dev/null)
if [ -z "$DLG" ]; then echo "$SCEN${XCLOCK:+ xclock=$XCLOCK}: no confirmation window"; else
	echo "$SCEN${XCLOCK:+ xclock=$XCLOCK}: dialog $DLG above-doc=$(above $DLG $DOC) above-xclock=$(above $DLG $XC) active=$([ $((DLG)) = $((ACT)) ] && echo yes || echo "NO($ACT)") $(xprop -id $DLG _NET_WM_STATE | sed 's/.*= //') $UT"
fi | tee "$OUT/verdict.txt"
[ -n "$KEEP" ] && { sleep $KEEP; exit 0; }
[ -n "$XPID" ] && kill $XPID
w $RT/bin/wineserver -k; sleep 2
rm -rf "$WINEPREFIX"
