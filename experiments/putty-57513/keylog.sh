#!/bin/sh
# layout $1, XMODIFIERS=@im=$2: run keylog.exe, press 2 Cyrillic keys
set -u
eval "$(dbus-launch --sh-syntax)"
if [ "$2" = ibus ]; then ibus-daemon --xim --daemonize --panel disable --replace >/dev/null 2>&1; for _ in $(seq 50); do ibus engine >/dev/null 2>&1 && break; sleep .2; done; ibus engine xkb:us::eng; sleep .5; fi
setxkbmap -layout us,ru
XMODIFIERS=@im=$2 /opt/wine-stable/bin/wine /home/claude/work/putty/keylog.exe ${3:-} > /home/claude/work/putty/keylog-$1-$2.txt 2>/home/claude/work/putty/trace-$1-$2.txt &
t=0; until w=$(xdotool search --onlyvisible --name '^keylog$' 2>/dev/null | tail -1) && [ -n "$w" ] || [ $t -ge 60 ]; do sleep 1; t=$((t+1)); done
sleep 1; xdotool windowactivate --sync "$w"; sleep .5
X=/home/claude/work/putty/xkey.py; [ "$1" = ru ] && python3 $X group 1; python3 $X keys 24 25; python3 $X group 0
sleep 1; /opt/wine-stable/bin/wineserver -k; ibus exit >/dev/null 2>&1; kill $DBUS_SESSION_BUS_PID 2>/dev/null; :
