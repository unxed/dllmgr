#!/bin/sh
# ps-batch.sh VARIANT OUT PREFIX [LAUNCH...]: Photoshop CS2 startup measurements
# in one stand session (#87). Phase A: launch -> "Adobe Activation" dialog and
# CPU quiet (plug-in scan included). The first run of a fresh prefix copy
# also clicks Continue Trial (phase B: -> main window quiet); later starts of
# the copy get the "trial over" variant of the dialog (F25), phase A only.
# LAUNCH defaults to plain stock `wine Photoshop.exe`. PHASES as in fs-batch.sh.
V=$1 OUT=$2 PFX=$3; shift 3
[ $# -gt 0 ] || set -- /opt/wine-stable/bin/wine Photoshop.exe
set -f
PHASES=${PHASES:-first warm cold strace}
has() { case " $PHASES " in *" $1 "*) return 0;; esac; return 1; }
T=$(cd "$(dirname "$0")/../../tools/perf" && pwd)
S="python3 $T/startup.py --prefix $PFX --wine-log $PFX/.dllmgr/runs/*.log --wine-log $PFX/.dllmgr/trampoline-run.log --timeout 180 --quiet-ms 2000"
cd "$PFX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
has first && $S --out $OUT/$V-first --step 'Adobe Activation' --do 'xdotool mousemove 1788 1372 click 1' --step '^Adobe Photoshop$' --shot $OUT/$V-first.png -- "$@" > $OUT/$V-first.txt 2>&1
has warm && for i in 1 2; do $S --out $OUT/$V-warm$i --step 'Adobe Activation' --shot $OUT/$V-warm$i.png -- "$@" > $OUT/$V-warm$i.txt 2>&1; done
has cold && $S --out $OUT/$V-cold1 --step 'Adobe Activation' --cold /opt/wine-stable "$PFX" ${RT:-} -- "$@" > $OUT/$V-cold1.txt 2>&1
has strace && $S --out $OUT/$V-strace --strace --step 'Adobe Activation' -- "$@" > $OUT/$V-strace.txt 2>&1
has server && $S --out $OUT/$V-server --server-trace --wineserver ${WINESERVER:-/opt/wine-stable/bin/wineserver} --step 'Adobe Activation' -- "$@" > $OUT/$V-server.txt 2>&1
