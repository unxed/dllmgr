#!/bin/sh
# Build the dllmgr-27 prefill proxy (i686, for 32-bit apps):
#   sh build.sh [msimg32|version] [out.dll]
# msimg32: FastStone 8.5 entry; version: earlier entry (loaded before
# Photoshop CS2's UI modules). Same prefill.c in both.
set -eu
cd "$(dirname "$0")"
kind=${1:-msimg32}
out=${2:-$kind.dll}
case "$kind" in
	msimg32) extra= ;;
	version) extra="version-stubs.c -DDLLMGR27_CAPTIONLESS_ONLY -DDLLMGR27_ACTIVE_IN_RUNTIME" ;;  # Photoshop: splash only, also under the private runtime
	*) echo "unknown proxy $kind" >&2; exit 2 ;;
esac
# vSetDdrawflag is only exported by msimg32.def; harmless in version.dll.
i686-w64-mingw32-gcc -O2 -Wall -shared -s -o "$out" prefill.c $extra "$kind.def" \
	-Wl,--enable-stdcall-fixup -Wl,--kill-at -lgdi32 -luser32
echo "built $out"
