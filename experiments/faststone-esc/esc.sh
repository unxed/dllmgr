#!/bin/sh
# #39 probe: when does Esc start closing FastStone? MODE=private|stock
set -u
mode=$1
P=/home/claude/work/first-open/prefix E=/home/claude/work/fs-e2e/FSViewer85/FSViewer.exe IMG=/home/claude/work/tramp/a.jpg
now() { date +%s%3N; }
/home/claude/work/first-open/xsample f0cc5a 6000 > /home/claude/work/esc/x-$mode.txt &
xs=$!
t0=$(now)
if [ "$mode" = private ]; then
  python3 /home/claude/dllmgr/scripts/private-app.py run --prefix $P --exe $E -- $IMG >/dev/null 2>&1 &
else
  DLLMGR27_OFF=1 WINEDLLOVERRIDES=msimg32=b /opt/wine-stable/bin/wine $E 'Z:\home\claude\work\tramp\a.jpg' >/dev/null 2>&1 &
fi
tmap=-; n=0; first_focus=-
sleep .3
while pgrep -f FSViewer.exe >/dev/null || [ $(( $(now) - t0 )) -lt 1500 ]; do f=$(xdotool getwindowfocus getwindowname 2>/dev/null); case "$f" in *FastStone*|*a.jpg*|*Fsviewer*) [ "$first_focus" = - ] && first_focus=$(( $(now) - t0 ));; esac; xdotool key Escape; n=$((n+1)); sleep .1; [ $(( $(now) - t0 )) -gt 20000 ] && break; done
texit=$(( $(now) - t0 ))
wait $xs
echo "mode=$mode first_fs_focus_ms=$first_focus exit_ms=$texit esc_presses=$n alive_after=$(pgrep -fc FSViewer.exe) $(tail -1 /home/claude/work/esc/x-$mode.txt)"
/opt/wine-stable/bin/wineserver -k 2>/dev/null; :
