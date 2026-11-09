#!/bin/sh
# mini2.sh DLL LABEL: Muffin stand :95; minimize Photoshop's main window during loading, report splash state
DLL=$1; L=$2; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"; O=/home/claude/work/cur/mini-$L.txt; : > $O
[ -f "$D/version.dll.keep" ] || cp "$D/version.dll" "$D/version.dll.keep"
cp "$DLL" "$D/version.dll"
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
env $EXTRA WINEDLLOVERRIDES=version=n,b setsid /opt/wine-stable/bin/wine "$D/Photoshop.exe" >/home/claude/work/cur/mini-$L.log 2>&1 &
until xdotool search --onlyvisible --class photoshop.exe >/dev/null 2>&1; do sleep .1; done
sleep 4; main=$(xdotool search --onlyvisible --name '^Adobe Photoshop$' | head -1)
xdotool windowminimize $main; sleep .5; xdotool windowactivate $(xdotool search --onlyvisible --class xlogo | head -1) 2>/dev/null; sleep 3
st() { for w in $(xdotool search --class photoshop.exe); do s=$(xwininfo -id $w | awk '/Map State/{print $3}'); [ "$s" = IsViewable ] && echo "  viewable $w '$(xdotool getwindowname $w)' $(xwininfo -id $w | awk '/Width|Height/{printf $2"x"}')"; done; echo "  main WM_STATE: $(xprop -id $main WM_STATE | sed -n 2p)"; }
echo "after minimize:" >> $O; st >> $O; import -window root -resize 20% /home/claude/work/cur/mini-$L-1.png
xdotool windowactivate $main 2>/dev/null; sleep 3; echo "after restore:" >> $O; st >> $O
cat $O; /opt/wine-stable/bin/wineserver -k; cp "$D/version.dll.keep" "$D/version.dll"
