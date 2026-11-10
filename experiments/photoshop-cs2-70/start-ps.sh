#!/bin/sh
# start-ps.sh TAG: start Photoshop (rt-cur3, C:\t46.png) and wait until the main window and the activation dialog are up
T=$1; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; RT=/home/claude/work/rt-cur3
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"; $RT/bin/wineserver -k 2>/dev/null; sleep 1
(env $EXTRA DLLMGR27_NO_TRAMPOLINE=1 WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver WINEDLLOVERRIDES=version=n,b setsid $RT/bin/wine Photoshop.exe 'C:\t46.png' > /home/claude/work/r41/${T}.log 2>&1 &)
timeout 200 sh -c 'until wmctrl -l | grep -q "Adobe Activation\|Continue Trial"; do sleep 2; done'; sleep 15
