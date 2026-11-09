#!/bin/sh
# #52 probe runner (stand :95, 192 DPI): text-aa.exe on stock Wine or the
# private runtime with a font-smoothing registry variant; crops the window.
# text-aa.sh OUT.png stock|RUNTIME_DIR [FontSmoothing FontSmoothingType]
# FontSmoothing/Type: "2 1" grayscale, "2 2" ClearType, "0 0" off, empty = prefix as is.
set -e
OUT=$1; RT=$2; FS=${3:-}; FT=${4:-}
H=$(cd "$(dirname "$0")" && pwd)
export DISPLAY=${DISPLAY:-:95} WINEPREFIX=${WINEPREFIX:-/home/claude/work/photoshop-cs2/prefix-auto}
EXE=${TEXTAA_EXE:-/home/claude/work/textaa/text-aa.exe}
if [ ! -f "$EXE" ]; then mkdir -p "$(dirname "$EXE")"; i686-w64-mingw32-gcc -O2 -o "$EXE" "$H/text-aa.c" -mwindows -lgdi32; fi
if [ "$RT" = stock ]; then W=/opt/wine-stable/bin/wine; S=/opt/wine-stable/bin/wineserver; set --
else W=$RT/bin/wine; S=$RT/bin/wineserver; set -- WINEARCH=wow64 WINELOADER=$W WINESERVER=$S; fi
$S -k 2>/dev/null || true; sleep 1
if [ -n "$FS" ]; then
  env "$@" $W reg add 'HKCU\Control Panel\Desktop' /v FontSmoothing /t REG_SZ /d "$FS" /f >/dev/null 2>&1
  env "$@" $W reg add 'HKCU\Control Panel\Desktop' /v FontSmoothingType /t REG_DWORD /d "$FT" /f >/dev/null 2>&1
  env "$@" $W reg add 'HKCU\Control Panel\Desktop' /v FontSmoothingOrientation /t REG_DWORD /d 1 /f >/dev/null 2>&1
fi
(env "$@" setsid $W "$EXE" >/dev/null 2>&1 &)
sleep 6
import -window root -crop 1000x620+0+0 "$OUT"
$S -k 2>/dev/null || true
