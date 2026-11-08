#!/bin/sh
# Build the dllmgr-38 feedback shim as a version.dll proxy:
#   sh build.sh [x86_64|i686] [out.dll]
# x86_64 for Photoshop 2024 (64-bit). Exports forward like
# patches/dllmgr-27/version.def.
set -eu
cd "$(dirname "$0")"
arch=${1:-x86_64}
out=${2:-version-$arch.dll}
"$arch-w64-mingw32-gcc" -O2 -Wall -shared -s -o "$out" shim.c ../dllmgr-27/version-stubs.c ../dllmgr-27/version.def \
	-Wl,--enable-stdcall-fixup -Wl,--kill-at -luser32 -lkernel32 -lpsapi
echo "built $out"
