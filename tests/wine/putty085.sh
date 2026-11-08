#!/bin/sh
# Fetch the pinned official PuTTY 0.85 putty.exe (released 2026-08-16) into DIR
# and verify it: sh tests/wine/putty085.sh DIR [w64|w32]
set -eu
dir=$1 arch=${2:-w64}
case "$arch" in
	w64) sum=d01fdb5aae8f112526040a39b0bfb9e27d813003178645e65f8d1cfdb2a26c87 ;;
	w32) sum=4c70267ca03a00ea761ec358498b990a7221decb36eace9b7dbe6a751be0fb3b ;;
	*) echo "arch: w64 or w32" >&2; exit 2 ;;
esac
mkdir -p "$dir"
f=$dir/putty-$arch.exe
[ -s "$f" ] || curl -fsSL -o "$f" "https://the.earth.li/~sgtatham/putty/0.85/$arch/putty.exe"
echo "$sum  $f" | sha256sum -c - >/dev/null || { echo "putty $arch checksum mismatch: $f" >&2; exit 1; }
echo "$f"
