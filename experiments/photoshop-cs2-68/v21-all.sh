#!/bin/sh
# v21-all.sh OUTDIR [SCEN...]: one stand session per scenario of v21-close.sh
# (fresh prefix copy each), display :132; prints the verdict lines.
# A scenario is SCEN or SCEN:XCLOCK (e.g. menu:1, altf4:click).
O=$1; shift
B=/home/unxed/.cache/dllmgr-agent/cc-rcnb-52ab
D=$(cd "$(dirname "$0")" && pwd)
export RT=${RT:-$B/home/.local/share/dllmgr/runtimes/c6d2b6d208f77517fd9f24f00e10a28a2a5f6217aa9656cddda1950b4a38642a}
for sc in ${*:-ctrlw menu altf4 closebtn menu:1 menu:click altf4:1 closebtn:1}; do
	s=${sc%%:*}; x=; [ "$s" != "$sc" ] && x=${sc#*:}
	n=$s${x:+-x$x}
	( . $B/env.sh; XCLOCK=$x SD=:132 SDIR=$B/sub3 timeout 600 $B/run.sh sh "$D/v21-close.sh" "$O/$n" $s ) > "$O/$n.log" 2>&1
	cp $B/sub3/wm.log "$O/$n/wm.log" 2>/dev/null   # Muffin log (MUFFIN_VERBOSE=1 for focus decisions)
	cat "$O/$n/verdict.txt" 2>/dev/null || { echo "$n: no verdict"; tail -3 "$O/$n.log"; }
done
