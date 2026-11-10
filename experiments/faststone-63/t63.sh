#!/bin/sh
# t63.sh OUT [COMCTL32]: FastStone the way `dllmgr run` starts it (RT, WINEPREFIX,
# EXE, BASE = the recipe's comctl32/gdiplus in Windows form), optionally with
# another comctl32 (Windows path), and crops of the path combo: normal, then
# with the pointer on the drop button (hot). Run inside a stand session.
# COMBO="X Y" is the drop button at 192 DPI on the 3072x1728 stand.
OUT=$1; CC=${2:-$BASE_COMCTL32}; mkdir -p "$OUT"; COMBO=${COMBO:-2684 374}
set -- $COMBO; X=$1; Y=$2
env WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver DLLMGR_TARGET_EXE="$TARGET" \
	DLLMGR_COMCTL32="$CC" DLLMGR_GDIPLUS="$BASE_GDIPLUS" WINEDLLOVERRIDES=msimg32=n,b WINEDEBUG=${WDBG:--all} \
	setsid $RT/bin/wine "$TARGET" > "$OUT/wine.log" 2>&1 &
for i in $(seq 40); do sleep 1; wmctrl -l | grep -q 'FastStone' && break; done; sleep 6
xdotool mousemove 1500 1500; sleep 1
import -window root -crop 640x80+$((X - 560))+$((Y - 40)) "$OUT/normal.png"
xdotool mousemove $X $Y; sleep 1
import -window root -crop 640x80+$((X - 560))+$((Y - 40)) "$OUT/hot.png"
import -window root "$OUT/full.png"
env WINESERVER=$RT/bin/wineserver $RT/bin/wineserver -k
