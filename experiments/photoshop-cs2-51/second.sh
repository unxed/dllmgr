#!/bin/sh
# second.sh: a stock Photoshop runs (no trampoline); then the private runtime starts a second instance, traced (#51)
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8
O=/home/claude/work/r41/second; mkdir -p $O
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
(DLLMGR27_NO_TRAMPOLINE=1 setsid /opt/wine-stable/bin/wine Photoshop.exe > $O/stock.log 2>&1 &)
sleep 40
S=$(date +%s); WINEDEBUG=+process,+loaddll timeout 60 ~/.local/bin/dllmgr run photoshop-cs2 > $O/private.log 2>&1; echo "private exit $? after $(( $(date +%s) - S )) s"
grep -c "" $O/private.log; grep "Photoshop.dll\|PSArt\|version.dll\|err:" $O/private.log | cut -c1-160 | head
/opt/wine-stable/bin/wineserver -k
