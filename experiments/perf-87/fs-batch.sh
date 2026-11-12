#!/bin/sh
# fs-batch.sh VARIANT OUT PREFIX FSDIR IMGDIR [LAUNCH...]: FastStone startup and
# thumbnail measurements in one stand session (#87). VARIANT names the output.
# LAUNCH defaults to plain stock `wine FSViewer.exe`; for the private runtime
# pass e.g. `dllmgr run faststone --prefix PREFIX --`. PHASES (default
# "warm cold thumbs strace") picks the runs; RT=runtime dir is evicted too.
V=$1 OUT=$2 PFX=$3 FSD=$4 IMG=$5; shift 5
[ $# -gt 0 ] || set -- /opt/wine-stable/bin/wine "$FSD/FSViewer.exe"
set -f  # --wine-log globs reach startup.py unexpanded
PHASES=${PHASES:-warm cold thumbs strace}
T=$(cd "$(dirname "$0")/../../tools/perf" && pwd)
S="python3 $T/startup.py --prefix $PFX --wine-log $PFX/.dllmgr/runs/*.log --wine-log $PFX/.dllmgr/trampoline-run.log --step ^FastStone.Image.Viewer --timeout 90"
WIMG="Z:$(echo "$IMG" | tr / '\\\\')"
cd "$FSD"
has() { case " $PHASES " in *" $1 "*) return 0;; esac; return 1; }
has warm && for i in 1 2 3; do $S --out $OUT/$V-warm$i -- "$@" > $OUT/$V-warm$i.txt 2>&1; done
has cold && for i in 1 2; do $S --out $OUT/$V-cold$i --cold /opt/wine-stable "$PFX" "$FSD" ${RT:-} -- "$@" > $OUT/$V-cold$i.txt 2>&1; done
# thumbnails: first open of the folder with FastStone's thumbnail cache
# (FSIV.db next to the portable FSViewer.exe) removed, then again cached
has thumbs && rm -f "$FSD"/FSIV.db*
has thumbs && for i in 1 2; do $S --out $OUT/$V-thumbs$i --shot $OUT/$V-thumbs$i.png -- "$@" "$WIMG" > $OUT/$V-thumbs$i.txt 2>&1; done
has server && $S --out $OUT/$V-server --server-trace --wineserver ${WINESERVER:-/opt/wine-stable/bin/wineserver} -- "$@" > $OUT/$V-server.txt 2>&1
has strace && $S --out $OUT/$V-strace --strace -- "$@" > $OUT/$V-strace.txt 2>&1
has strace && rm -f "$FSD"/FSIV.db*
has strace && $S --out $OUT/$V-strace-thumbs --strace -- "$@" "$WIMG" > $OUT/$V-strace-thumbs.txt 2>&1
