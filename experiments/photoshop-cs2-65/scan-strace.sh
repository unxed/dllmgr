#!/bin/sh
O=/home/claude/work/r41/scan2; mkdir -p $O
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8 DLLMGR_RUN_WATCH=
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
(~/.local/bin/dllmgr run photoshop-cs2 > $O/run.log 2>&1 &)
sleep 9
P=$(pgrep -f 'Photoshop.exe' | head -1); W=$(pgrep -x wineserver | head -1)
echo "ps=$P server=$W"
timeout 3 strace -f -e trace=openat,newfstatat -p $P -o $O/ps.trace 2>/dev/null &
sleep 3
sleep 1
grep -o "\"[^\"]*\"" $O/ps.trace | sort | uniq -c | sort -rn | head -25; wc -l < $O/ps.trace
/opt/wine-stable/bin/wineserver -k
