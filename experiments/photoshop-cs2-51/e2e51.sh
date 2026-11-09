#!/bin/sh
# e2e51.sh TAG DLL [ENV...]: plain launch with a given proxy; handover check (#51); restores the proxy
T=$1; DLL=$2; shift 2
PS="/home/claude/work/photoshop-cs2/prefix-auto/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
cp "$PS/version.dll" /home/claude/work/r41/version.dll.saved51 && cp "$DLL" "$PS/version.dll"
O=/home/claude/work/r41/$T; mkdir -p $O
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
cd "$PS"
(env "$@" DLLMGR27_DEBUG=1 setsid /opt/wine-stable/bin/wine Photoshop.exe > $O/wine.log 2>&1 &)
sleep 45
~/.local/bin/dllmgr status photoshop-cs2 > $O/status.txt 2>&1
grep -q 'on the private runtime' $O/status.txt && echo "$T handover: private runtime" || echo "$T handover: NO"
grep "trampoline" $O/wine.log | cut -c1-150
grep "Running:" $O/status.txt
/opt/wine-stable/bin/wineserver -k; sleep 1
cp /home/claude/work/r41/version.dll.saved51 "$PS/version.dll"
