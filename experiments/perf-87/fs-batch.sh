#!/bin/sh
# fs-batch.sh VARIANT OUT PREFIX FSDIR IMGDIR [LAUNCH...]: FastStone startup and
# thumbnail measurements in one stand session (#87). VARIANT names the output.
# LAUNCH defaults to plain stock `wine FSViewer.exe`; for the private runtime
# pass e.g. `dllmgr run faststone --prefix PREFIX --`.
V=$1 OUT=$2 PFX=$3 FSD=$4 IMG=$5; shift 5
[ $# -gt 0 ] || set -- /opt/wine-stable/bin/wine "$FSD/FSViewer.exe"
T=$(cd "$(dirname "$0")/../../tools/perf" && pwd)
S="python3 $T/startup.py --prefix $PFX --step ^FastStone.Image.Viewer --timeout 90"
WIMG="Z:$(echo "$IMG" | tr / '\\\\')"
cd "$FSD"
for i in 1 2 3; do $S --out $OUT/$V-warm$i -- "$@" > $OUT/$V-warm$i.txt 2>&1; done
for i in 1 2; do $S --out $OUT/$V-cold$i --cold /opt/wine-stable "$PFX" "$FSD" ${RT:-} -- "$@" > $OUT/$V-cold$i.txt 2>&1; done
# thumbnails: first open of the folder (no cached thumbnails), then again
for i in 1 2; do $S --out $OUT/$V-thumbs$i -- "$@" "$WIMG" > $OUT/$V-thumbs$i.txt 2>&1
  import -window root -resize 25% $OUT/$V-thumbs$i/end.png; done
$S --out $OUT/$V-strace --strace -- "$@" > $OUT/$V-strace.txt 2>&1
$S --out $OUT/$V-strace-thumbs --strace -- "$@" "$WIMG" > $OUT/$V-strace-thumbs.txt 2>&1
