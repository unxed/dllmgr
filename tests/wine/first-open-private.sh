#!/bin/sh
# #27 end-to-end through dllmgr's private runtime: launch an already installed
# private FastStone fix (`private-app.py install ... --runtime-package ZIP`) via
# `private-app.py run`, judge the first open by X pixels (xsample). Before each
# run, files FastStone created since FSVIEWER_DIR/../orig-files.txt are removed
# so every open is a first open. Run inside a stand session (STAND_WM=metacity):
#   sh tests/wine/first-open-private.sh FSVIEWER_EXE IMAGE XSAMPLE [DURATION_MS]
set -eu
exe=$1 image=$2 xsample=$3 duration=${4:-9000}
here=$(cd "$(dirname "$0")/../.." && pwd)
dir=$(dirname "$exe")
list=$(dirname "$dir")/orig-files.txt
if [ -f "$list" ]; then
	(cd "$dir" && find . -type f | sort | comm -13 "$list" - | while read -r f; do rm -f -- "$f"; done)
fi
out=$(mktemp)
"$xsample" f0cc5a "$duration" >"$out" &
spid=$!
python3 "$here/scripts/private-app.py" run --exe "$exe" -- "$image" >/dev/null 2>&1 &
wait $spid
cat "$out"
wineserver -k 2>/dev/null || :
summary=$(tail -1 "$out"); rm -f "$out"
case "$summary" in
	first_image_ms=-1*) echo "verdict=FAIL (image never shown)"; exit 1 ;;
	*interruptions_after_image=0*) echo "verdict=pass"; exit 0 ;;
	*) echo "verdict=FAIL (interruption after image)"; exit 1 ;;
esac
