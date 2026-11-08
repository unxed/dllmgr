#!/bin/sh
# #27 trampoline end-to-end (docs/tasks/27-every-launch-path.md): a stock
# `wine FSViewer.exe A` must end up in the private runtime (winex11.so from the
# dllmgr runtime cache), and a second stock start B must be forwarded there.
# FSDIR = the directory of the exe installed with the private fix, holding
# msimg32.dll (patches/dllmgr-27) and msimg32.dllmgr (launcher line). Run in a
# stand session:
#   WINEDLLOVERRIDES=msimg32=n,b sh scripts/sandbox-stand.sh session \
#     sh tests/wine/trampoline-e2e.sh WINE FSDIR A.jpg B.jpg
# Exit 0 when A runs under the private runtime and B is forwarded to it.
set -u
W=$1 FS=$2 A=$3 B=$4
export DLLMGR27_DEBUG=1
log=$(mktemp -d)
seen() { xdotool search --onlyvisible --name "$1" >/dev/null 2>&1; }
"$W" "$FS/FSViewer.exe" "$(winepath -w "$A" 2>/dev/null || echo "$A")" >"$log/a" 2>&1 &
t=0; until seen "${A##*/}" || [ $t -ge 240 ]; do sleep .5; t=$((t + 1)); done
rc=1
for p in $(pgrep -f 'FSViewer.exe'); do
	grep -q '/dllmgr/runtimes/.*/winex11.so' "/proc/$p/maps" 2>/dev/null && rc=0
done
echo "A: window=$(seen "${A##*/}" && echo yes || echo no) private_winex11=$([ $rc = 0 ] && echo yes || echo no)"
"$W" "$FS/FSViewer.exe" "$(winepath -w "$B" 2>/dev/null || echo "$B")" >"$log/b" 2>&1 &
t=0; until seen "${B##*/}" || [ $t -ge 120 ]; do sleep .5; t=$((t + 1)); done
sleep 2
for _ in 1 2 3 4 5 6; do [ "$(pgrep -fc FSViewer.exe)" = 1 ] && break; sleep 1; done
n=$(pgrep -fc 'FSViewer.exe')
echo "B: window=$(seen "${B##*/}" && echo yes || echo no) fsviewer_processes=$n"
{ seen "${B##*/}" && [ "$n" = 1 ]; } || rc=1
grep -h 'dllmgr27.*trampoline\|proxy idle' "$log/a" "$log/b"
rm -rf "$log"
"$(dirname "$W")/wineserver" -k 2>/dev/null || :
echo "verdict=$([ $rc = 0 ] && echo pass || echo FAIL)"
exit $rc
