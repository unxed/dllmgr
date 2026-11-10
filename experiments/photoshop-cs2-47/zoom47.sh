#!/bin/sh
# zoom47.sh OUT: dllmgr run with C:\t46.png, Alt+wheel up at the image centre, record the screen at 30 fps (#47)
O=$1; mkdir -p $O; rm -f $O/*.png
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
(setsid ~/.local/bin/dllmgr run photoshop-cs2 -- 'C:\t46.png' > $O/run.log 2>&1 &)
sleep 45
xdotool mousemove 1788 1372 click 1; sleep 4; wmctrl -c 'Adobe Updater Preferences'; sleep 2
F=$(xdotool search --name '^Adobe Photoshop$' | head -1); xdotool windowactivate --sync "$F"; sleep 1
xdotool mousemove 1000 800; sleep 1
ffmpeg -loglevel error -f x11grab -framerate 30 -video_size 3072x1728 -i :95 -t 4 -vf "crop=2000:1500:100:150,scale=1000:750" $O/f%03d.png &
FF=$!; sleep 0.7
xdotool keydown alt; xdotool click 4; sleep 1.2; xdotool click 4; sleep 0.3; xdotool keyup alt
wait $FF
ls $O/f*.png | wc -l
/opt/wine-stable/bin/wineserver -k
