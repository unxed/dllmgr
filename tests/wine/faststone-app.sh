#!/usr/bin/env bash
set -euo pipefail
export WINEPREFIX=$RUNNER_TEMP/fs75 WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
wineboot -u
curl -fsSL --retry 3 --max-time 120 https://www.faststonesoft.net/DN/FSViewer75.zip -o fs75.zip
echo 'cbe75459879bfcb330c26e7ce4378270691f290c1c903bf2993d7eb276ea6441  fs75.zip' | sha256sum -c
unzip -q fs75.zip
python3 tests/wine/make-images.py
wine FSViewer75/FSViewer.exe "Z:$(pwd | sed 's,/,\\,g')\\images\\white.bmp" > app.log 2>&1 &
sleep 8
mkdir -p snapshots
scrot snapshots/01-open.png
xdotool getactivewindow getwindowname
xdotool key d
sleep 3
scrot snapshots/02-draw.png
xwininfo -root -tree > snapshots/windows.txt
cp app.log snapshots/
wineserver -k
