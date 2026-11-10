#!/bin/sh
# t73c.sh OUT: the owner's path end to end: `dllmgr run faststone` (installed recipe),
# F12 Settings, Associations tab, "Association Settings" button; is dllmgr's dialog shown?
# Coordinates: TAB/BTN env ("X Y"); defaults are the Russian UI on the 3072x1728 192-DPI stand.
# Run inside a stand session (DISPLAY set, dllmgr in PATH, recipe installed).
OUT=$1; mkdir -p "$OUT"
dllmgr run faststone > "$OUT/run.log" 2>&1 &
for i in $(seq 40); do sleep 1; wmctrl -l | grep -q 'FastStone' && break; done; sleep 6
import -window root "$OUT/1-browser.png"
xdotool key F12; sleep 5; import -window root "$OUT/2-settings.png"
xdotool mousemove ${TAB:-1590 352} click 1; sleep 2; import -window root "$OUT/3-assoc-tab.png"
xdotool mousemove ${BTN:-1212 750} click 1
for i in $(seq 20); do sleep 1; wmctrl -l | grep -qi 'file types\|associat' && break; done; sleep 2
import -window root "$OUT/4-after-button.png"
wmctrl -l | cut -c20- | tee "$OUT/windows.txt"
pgrep -af zenity > "$OUT/zenity.txt"; cat "$OUT/zenity.txt"
pkill zenity; dllmgr status faststone > "$OUT/status.txt" 2>&1; tail -3 "$OUT/status.txt"
