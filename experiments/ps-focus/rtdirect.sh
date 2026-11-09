#!/bin/sh
# rtdirect.sh RT LABEL: Photoshop on runtime dir RT directly (no trampoline), proxy = version-bis2.dll; frame at +1.5 s
export WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto DISPLAY=:95; RT=$1; L=$2; C=/home/claude/work/cur
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"; cp $C/version-bis2.dll "$D/version.dll"
(cd "$D" && WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b DLLMGR27_NO_TRAMPOLINE=1 setsid $RT/bin/wine Photoshop.exe >/dev/null 2>&1 &)
t=0; until xdotool search --onlyvisible --name '^Adobe Photoshop$' >/dev/null 2>&1 || [ $t -ge 400 ]; do sleep .2; t=$((t+1)); done
sleep 1.5; import -window root -resize 25% $C/dir-$L.png
timeout 10 $RT/bin/wineserver -k; sleep 1; cp $C/version-pkg.dll "$D/version.dll"
