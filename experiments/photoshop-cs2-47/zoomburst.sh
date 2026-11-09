#!/bin/sh
# zoomburst.sh LABEL WINE_DIR|stock: #47. open C:\t46.png, zoom tool, click canvas, capture 20 frames fast
L=$1; RT=$2; export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto; C=/home/claude/work/cur
D="$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2"
if [ "$RT" = stock ]; then E=""; W=/opt/wine-stable/bin/wine; S=/opt/wine-stable/bin/wineserver; else E="WINEARCH=wow64 WINELOADER=$RT/bin/wine WINESERVER=$RT/bin/wineserver"; W=$RT/bin/wine; S=$RT/bin/wineserver; fi
(cd "$D" && env $E setsid $W Photoshop.exe 'C:\t46.png' >/dev/null 2>&1 &)
sleep 100; xdotool mousemove 104 748 click 1; sleep 1; xdotool mousemove 900 800; sleep 1
mkdir -p $C/zb-$L
(for i in $(seq -w 1 20); do import -window root -crop 1400x1000+200+250 -resize 30% $C/zb-$L/$i.png; done) &
CAP=$!; sleep .1; xdotool click 1; wait $CAP
montage $C/zb-$L/*.png -tile 10x2 -geometry +2+2 $C/zb-$L.png
timeout 10 $S -k; sleep 1
