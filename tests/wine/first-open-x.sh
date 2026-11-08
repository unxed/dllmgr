#!/bin/sh
# #27 first-open check judged by X pixels: fresh copy of portable FastStone 8.5,
# open the synthetic JPEG, sample the screen with xsample for DURATION ms.
# Run inside a stand session with STAND_WM=metacity (no compositing):
#   STAND_WM=metacity sh scripts/sandbox-stand.sh session \
#     sh tests/wine/first-open-x.sh WINE_BIN FSVIEWER85_DIR XSAMPLE_BIN [DURATION_MS]
# Prints xsample transitions + summary; exit 0 if the image showed and no
# interruption followed it, 1 otherwise.
set -eu
wine=$1 fsdir=$2 xsample=$3 duration=${4:-9000}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
cp -r "$fsdir" "$work/fs"
cp "$here/fixtures/first-open.jpg" "$work/synthetic.jpg"
"$xsample" f0cc5a "$duration" >"$work/x.txt" &
spid=$!
"$wine" "$work/fs/FSViewer.exe" "$(winepath -w "$work/synthetic.jpg" 2>/dev/null || echo "$work/synthetic.jpg")" >/dev/null 2>&1 &
wait $spid
cat "$work/x.txt"
"$(dirname "$wine")/wineserver" -k 2>/dev/null || :
summary=$(tail -1 "$work/x.txt")
rm -rf "$work"
case "$summary" in
	first_image_ms=-1*) echo "verdict=FAIL (image never shown)"; exit 1 ;;
	*interruptions_after_image=0*) echo "verdict=pass"; exit 0 ;;
	*) echo "verdict=FAIL (interruption after image)"; exit 1 ;;
esac
