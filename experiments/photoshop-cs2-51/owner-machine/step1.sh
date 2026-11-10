#!/bin/sh
set -eu
ROOT=/tmp/opencode/opencode-owner-51a7
test "$WINEPREFIX" = "$ROOT/prefix"
test "$DISPLAY" = :151
export XDG_DATA_HOME="$ROOT/data"
OUT="$ROOT/step1"
mkdir -p "$OUT"
dllmgr fix photoshop-cs2 --prefix "$WINEPREFIX" >"$OUT/fix.log" 2>&1
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
# Refuse to run if the trampoline still targets the owner's original prefix.
grep -F -- "--prefix \"$WINEPREFIX\"" "$PS/version.dllmgr" >"$OUT/companion.txt"
/opt/wine-stable/bin/wineserver -k || :
sleep 2
cd "$PS"
date -Iseconds >"$OUT/start-time.txt"
/opt/wine-stable/bin/wine Photoshop.exe >"$OUT/stock.log" 2>&1 &
sleep 45
dllmgr status photoshop-cs2 --prefix "$WINEPREFIX" >"$OUT/status.txt" 2>&1
wmctrl -lx >"$OUT/windows.txt"
for name in launch.log trampoline-run.log; do
    test ! -f "$WINEPREFIX/.dllmgr/$name" || cp "$WINEPREFIX/.dllmgr/$name" "$OUT/$name"
done
cat "$OUT/status.txt"
