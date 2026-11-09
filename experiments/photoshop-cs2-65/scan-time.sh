#!/bin/sh
# scan-time.sh OUT: start via dllmgr run, sample the splash status line every 2 s for 120 s (#65)
O=$1; mkdir -p $O
export DISPLAY=:95 WINEPREFIX=/home/claude/work/photoshop-cs2/prefix-auto LC_ALL=C.UTF-8
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
S=$(date +%s.%N)
(WINEDEBUG=+timestamp,+loaddll setsid ~/.local/bin/dllmgr run photoshop-cs2 > $O/run.log 2>&1 &)
i=0; prev=
while [ $i -lt 60 ]; do
  sleep 2; i=$((i+1))
  import -window root -crop 700x40+1170+540 +repage $O/s.png 2>/dev/null
  h=$(md5sum < $O/s.png | cut -c1-8)
  if [ "$h" != "$prev" ]; then t=$(echo "$(date +%s.%N) - $S" | bc | cut -c1-5); cp $O/s.png $O/s-$t.png; echo "t=$t change"; prev=$h; fi
  wmctrl -l | grep -q "Adobe Activation" && { echo "t=$(echo "$(date +%s.%N) - $S" | bc | cut -c1-5) activation dialog"; break; }
done
/opt/wine-stable/bin/wineserver -k
