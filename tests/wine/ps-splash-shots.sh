#!/bin/sh
# #36: capture the Photoshop CS2 splash over time on the sandbox stand.
# Run inside a stand session (WINEPREFIX = prefix with CS2 installed):
#   STAND_WM=metacity sh scripts/sandbox-stand.sh session \
#     sh tests/wine/ps-splash-shots.sh WINE_BIN OUT_DIR [SHOTS] [INTERVAL_S]
# Writes OUT_DIR/splash-NN.png (full) and splash-NN-s.png (25 %), then kills the
# prefix's wineserver. Photoshop is only started and observed, never driven.
set -eu
wine=$1 out=$2 shots=${3:-16} interval=${4:-0.5}
mkdir -p "$out"
exe="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe"
"$wine" "$exe" >"$out/ps.log" 2>&1 &
until xdotool search --onlyvisible --name 'Adobe Photoshop' >/dev/null 2>&1; do sleep .1; done
i=0
while [ $i -lt "$shots" ]; do
	n=$(printf %02d $i)
	import -window root "$out/splash-$n.png"
	convert "$out/splash-$n.png" -resize 25% "$out/splash-$n-s.png"
	i=$((i + 1)); sleep "$interval"
done
"$(dirname "$wine")/wineserver" -k 2>/dev/null || :
