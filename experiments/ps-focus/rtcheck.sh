#!/bin/sh
# rtcheck.sh DLL LABEL: under the installed PS-3 (trampoline -> runtime), Muffin :95:
# splash frames, minimize/restore, another app over the splash
export WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto DISPLAY=:95; L=$2; C=/home/claude/work/cur
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"; cp "$1" "$D/version.dll"
(cd "$D" && env DLLMGR27_DEBUG=1 $EXTRA setsid /opt/wine-stable/bin/wine Photoshop.exe >$C/rt-$L.log 2>&1 &)
t=0; until xdotool search --onlyvisible --name '^Adobe Photoshop$' >/dev/null 2>&1 || [ $t -ge 400 ]; do sleep .2; t=$((t+1)); done
for k in 1 2; do sleep 1; import -window root -crop 1500x1000+780+380 -resize 30% $C/rt-$L-$k.png; done
main=$(xdotool search --onlyvisible --name '^Adobe Photoshop$' | head -1); xdotool windowminimize $main; sleep 3
import -window root -resize 15% $C/rt-$L-min.png; echo "$L main $(xprop -id $main WM_STATE | sed -n 2p | tr -d '\t')"
xdotool windowactivate $main; sleep 2; import -window root -crop 1500x1000+780+380 -resize 30% $C/rt-$L-res.png
xlogo -geometry 1400x1000+800+400 & sleep 2; timeout 5 xdotool windowactivate $(xdotool search --onlyvisible --class xlogo | head -1); sleep 2
import -window root -resize 15% $C/rt-$L-over.png; pkill xlogo
timeout 10 /opt/wine-stable/bin/wineserver -k; sleep 1; cp $C/version-pkg.dll "$D/version.dll"
grep -a 'adopt' $C/rt-$L.log
cd $C && montage rt-$L-1.png rt-$L-2.png rt-$L-res.png rt-$L-min.png rt-$L-over.png -tile 5x1 -geometry 300x+3+3 rt-$L-m.png
