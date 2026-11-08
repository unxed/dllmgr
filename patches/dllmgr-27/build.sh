#!/bin/sh
# Build the dllmgr-27 proxy msimg32.dll (i686 for 32-bit FastStone 8.5).
set -eu
cd "$(dirname "$0")"
out=${1:-msimg32.dll}
i686-w64-mingw32-gcc -O2 -Wall -shared -s -o "$out" prefill.c msimg32.def \
	-Wl,--enable-stdcall-fixup -Wl,--kill-at -lgdi32 -luser32
echo "built $out"
