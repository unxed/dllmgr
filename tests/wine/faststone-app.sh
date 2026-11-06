#!/usr/bin/env bash
set -euo pipefail
export WINEPREFIX=$RUNNER_TEMP/fs75 WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
wineboot -u
curl -fsSL --retry 3 --max-time 120 https://www.faststonesoft.net/DN/FSViewer75.zip -o fs75.zip
echo 'cbe75459879bfcb330c26e7ce4378270691f290c1c903bf2993d7eb276ea6441  fs75.zip' | sha256sum -c
unzip -q fs75.zip
python3 tests/wine/make-images.py
WINEDEBUG=+gdiplus wine FSViewer75/FSViewer.exe "Z:$(pwd | sed 's,/,\\,g')\\images\\white.bmp" > app.log 2>&1 &
sleep 8
mkdir -p snapshots
scrot snapshots/01-open.png
xdotool getactivewindow getwindowname
xdotool key Escape
sleep 1
scrot snapshots/01b-browser.png
xdotool key Return
sleep 1
xdotool key d
sleep 3
scrot snapshots/02-draw.png
xdotool mousemove 16 232 click 1
sleep 1
scrot snapshots/03-pencil.png
xdotool mousemove 550 300 mousedown 1 mousemove --sync 850 500 mouseup 1
sleep 1
scrot snapshots/04-stroke.png
xwininfo -root -tree > snapshots/windows.txt
cp app.log snapshots/
wineserver -k
