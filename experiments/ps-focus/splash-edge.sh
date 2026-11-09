#!/bin/sh
# splash-edge.sh TAG DLL: splash capture with a given version.dll proxy, then restore; fringe count
T=$1; DLL=$2; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; RT=/home/claude/work/rt-cur3
PS="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
$RT/bin/wineserver -k 2>/dev/null; sleep 1
cp "$PS/version.dll" /home/claude/work/r41/version.dll.saved && cp "$DLL" "$PS/version.dll"
cd "$PS"
(DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b WINEDEBUG=-all setsid $RT/bin/wine Photoshop.exe > /home/claude/work/r41/$T.log 2>&1 &)
sleep 13; import -window root /home/claude/work/r41/$T-splash.png
$RT/bin/wineserver -k; sleep 1
cp /home/claude/work/r41/version.dll.saved "$PS/version.dll"
python3 /home/claude/work/r41/fringe.py /home/claude/work/r41/$T-splash.png
