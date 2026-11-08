#!/usr/bin/env bash
set -euo pipefail
src=$RUNNER_TEMP/wine-source
bld=$RUNNER_TEMP/wine-build
mkdir -p "$bld" out/isolation
 git clone -q --depth 1 --branch wine-11.0 https://github.com/wine-mirror/wine.git "$src"
test "$(git -C "$src" rev-parse HEAD)" = db11d0fe6a169c457e23d007e20404643d067aa8
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/wine-11.0-app-isolation.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/wine-11.0-app-isolation.patch"
(cd "$bld" && "$src/configure" --enable-archs=i386,x86_64 --without-x --with-freetype --with-fontconfig > configure.log 2>&1) || { tail -80 "$bld/configure.log"; exit 1; }
make -C "$bld" -j"$(nproc)" __tooldeps__ dlls/ntdll/all tools/wine/wine dlls/gdiplus/all dlls/comctl32_v6/all > "$bld/make.log" 2>&1 || { tail -100 "$bld/make.log"; exit 1; }
for arch in i386 x86_64; do
    mkdir -p "out/isolation/$arch-windows"
    cp "$bld/dlls/ntdll/$arch-windows/ntdll.dll" "out/isolation/$arch-windows/"
done
mkdir -p out/isolation/x86_64-unix out/isolation/bin
cp "$bld/dlls/ntdll/ntdll.so" out/isolation/x86_64-unix/
cp "$bld/tools/wine/wine" out/isolation/bin/
cp patches/wine-11.0-app-isolation.patch out/isolation/
printf '%s\n' 'wine-11.0 db11d0fe6a169c457e23d007e20404643d067aa8 + wine-11.0-app-isolation.patch' > out/isolation/SOURCE.txt
(cd out/isolation && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
