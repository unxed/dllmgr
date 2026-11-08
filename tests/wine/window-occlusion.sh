#!/bin/sh
# Run window-occlusion.exe on the current $DISPLAY and cover its centre with an
# xlogo window for ~1 s once it reports stage=painted. Prints the probe output;
# exit 0 when X shows the old content (yellow) or a repaint (red) after uncover.
# Usage (sandbox): STAND_WM=metacity sh scripts/sandbox-stand.sh session \
#   sh tests/wine/window-occlusion.sh WINE_BIN PROBE_EXE
set -eu
wine=$1 probe=$2 out=$(mktemp)
"$wine" "$probe" >"$out" 2>"${OCC_LOG:-/dev/null}" &
pid=$!
until grep -q 'stage=painted' "$out" 2>/dev/null; do sleep .05; done
eval "$(xdotool getdisplaygeometry --shell)"
xlogo -geometry 400x400+$((WIDTH / 2 - 200))+$((HEIGHT / 2 - 200)) &
logo=$!
sleep 1; [ -n "${OCC_SHOT:-}" ] && import -window root "$OCC_SHOT" || :
import -window root png:- | convert png:- -crop 1x1+$((WIDTH / 2))+$((HEIGHT / 2)) -format 'stage=xcovered rgb=%[hex:p{0,0}]\n' info:
kill $logo; sleep 1.5
after=$(import -window root png:- | convert png:- -crop 1x1+$((WIDTH / 2))+$((HEIGHT / 2)) -format '%[hex:p{0,0}]' info:)
echo "stage=xuncovered rgb=$after"
wait $pid || :
cat "$out"; rm -f "$out"
# Verdict from the X server's pixels, NOT from the probe's GetPixel: Wine's
# screen-DC GetPixel returned the window surface (yellow) while X showed black.
case "$after" in
	F0CC5A|FF0000) echo "verdict=pass"; exit 0 ;;
	*) echo "verdict=FAIL (X shows $after after uncover)"; exit 1 ;;
esac
