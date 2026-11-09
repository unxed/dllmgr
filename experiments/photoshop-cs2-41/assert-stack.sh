#!/bin/sh
# #62: stop Photoshop at the SLOCoolTypeFont.cpp:1633 throw (0x01078d08) with
# Linux gdb attached to the Wine process and dump the 32-bit stack: return
# addresses inside Photoshop.exe / its DLLs show the call chain (no PE
# debug info, so the stack is scanned instead of unwound).
# assert-stack.sh OUT [DOCUMENT]
OUT=$1; DOC=${2:-C:\\t46.png}
export DISPLAY=${DISPLAY:-:95} WINEPREFIX=${WINEPREFIX:-/home/claude/work/photoshop-cs2/prefix-auto}
cd "$WINEPREFIX/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2" || exit 1
/opt/wine-stable/bin/wineserver -k 2>/dev/null; sleep 1
(DLLMGR27_NO_TRAMPOLINE=1 setsid /opt/wine-stable/bin/wine Photoshop.exe "$DOC" >/dev/null 2>&1 &)
sleep 12; PID=$(pgrep -f "Photoshop.exe" | tail -1); echo "pid $PID: $(tr "\0" " " < /proc/$PID/cmdline)" >&2

cat > "$OUT.gdb" <<'EOF'
set pagination off
set confirm off
handle SIGUSR1 SIGUSR2 SIGSEGV SIGILL SIGBUS SIGFPE SIGTRAP SIGQUIT SIGALRM SIGPIPE SIGCHLD nostop noprint pass
handle SIGTRAP stop print nopass
break *0x01078d08
continue
info registers eip esp ebp
x/160wx $esp
x/4wx 0x14c6c38
x/2wx $esp+0x84+0x18
detach
quit
EOF
timeout 240 gdb -q -batch -x "$OUT.gdb" -p "$PID" > "$OUT" 2>&1 &
sleep 200; cp /proc/$PID/maps "$OUT.maps" 2>/dev/null; wait
/opt/wine-stable/bin/wineserver -k
