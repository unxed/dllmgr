#!/bin/sh
# 57513 probe: IBus as XIM input method, X keyboard layout $1 (us / ru), PuTTY raw
# connection to a local TCP sink; type keys q w e; print the bytes received.
set -u
engine=$1 exe=$2 im=${3:-ibus} out=/home/claude/work/putty/recv-$1-${3:-ibus}.bin
eval "$(dbus-launch --sh-syntax)"
[ "$im" = ibus ] && { ibus-daemon --xim --daemonize --panel disable --replace >/dev/null 2>&1; for _ in $(seq 50); do ibus engine >/dev/null 2>&1 && break; sleep .2; done; }
if [ "$im" = ibus ]; then ibus engine xkb:us::eng; sleep .5; fi; setxkbmap -layout us,ru; echo "LANG=$LANG im=$im group=$engine"
rm -f "$out"
python3 - "$out" <<'PY' &
import socket,sys
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(('127.0.0.1',5555)); s.listen(1)
c,_=s.accept(); f=open(sys.argv[1],'wb')
c.settimeout(60)
try:
    while True:
        d=c.recv(4096)
        if not d: break
        f.write(d); f.flush()
except Exception: pass
PY
sink=$!
sleep .5
XMODIFIERS=@im=$im /opt/wine-stable/bin/wine "$exe" -raw -P 5555 127.0.0.1 >/home/claude/work/putty/wine-$engine-$im.log 2>&1 &
t=0; until w=$(xdotool search --onlyvisible --class putty 2>/dev/null | tail -1) && [ -n "$w" ] || [ $t -ge 60 ]; do sleep 1; t=$((t+1)); done
echo "window: ${w:-none} after ${t}s: $(xdotool getwindowname "$w" 2>/dev/null)"
sleep 2
xdotool windowactivate --sync "$w" 2>/dev/null; sleep .5
X=/home/claude/work/putty/xkey.py; [ "$engine" = ru ] && python3 $X group 1; python3 $X keys 24 25 26; python3 $X group 0; python3 $X keys 36
sleep 2
import -window root /home/claude/work/putty/shot-$engine.png 2>/dev/null
printf 'received: '; od -An -tx1 "$out" 2>/dev/null | tr -s ' '; echo
printf 'as text: '; cat "$out" 2>/dev/null; echo
/opt/wine-stable/bin/wineserver -k; kill $sink 2>/dev/null; ibus exit >/dev/null 2>&1; kill $DBUS_SESSION_BUS_PID 2>/dev/null
