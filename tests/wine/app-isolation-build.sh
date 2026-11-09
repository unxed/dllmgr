#!/usr/bin/env bash
set -euo pipefail
src=$RUNNER_TEMP/wine-source
bld=$RUNNER_TEMP/wine-build
mkdir -p "$bld" out/isolation
 git clone -q --depth 1 --branch wine-11.0 https://github.com/wine-mirror/wine.git "$src"
test "$(git -C "$src" rev-parse HEAD)" = db11d0fe6a169c457e23d007e20404643d067aa8
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/wine-11.0-app-isolation.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/wine-11.0-app-isolation.patch"
# Issue 27: Unix-side window surface fix, shipped as the optional overlay group
# win32u.so + winex11.so (scripts/private_runtime.py OPTIONAL_GROUPS).
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/winehq-60721.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/winehq-60721.patch"
# Issue 43: activation requests as EWMH application requests with the last user
# time (not pager requests), so the WM can stop a background app stealing focus.
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-43.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-43.patch"
# Issue 44: custom cursors of DPI-scaled (virtualized) windows scaled like the
# window contents (32x32 -> 64x64 at 192 DPI), as Windows does.
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-44.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-44.patch"
# Issue 46: exact pixel blocks at integer DPI scales (no halftone spread that
# XOR-drawn brush outlines leave behind); +1 px dirty margin otherwise.
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-46.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-46.patch"
# Issue 49: shortcuts with a Russian (Cyrillic) layout: physical scancodes
# for evdev keyboards, the reported layout follows the active XKB group, and
# ToUnicodeEx for an explicit US layout answers from the US table.
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-49.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-49.patch"
# Issue 52: user-selectable text smoothing (DLLMGR52_TEXT, DLLMGR52_GAMMA):
# smoothing at every size like Windows ClearType, light hinting, contrast.
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-52.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-52.patch"
# #65: shell32 remembers folders without desktop.ini (plug-in scan 15 s -> ~0)
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-65.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-65.patch"
(cd "$bld" && "$src/configure" --enable-archs=i386,x86_64 --with-x --with-freetype --with-fontconfig > configure.log 2>&1) || { tail -80 "$bld/configure.log"; exit 1; }
make -C "$bld" -j"$(nproc)" __tooldeps__ dlls/ntdll/all tools/wine/wine dlls/gdiplus/all dlls/comctl32_v6/all dlls/win32u/all dlls/winex11.drv/all dlls/shell32/all > "$bld/make.log" 2>&1 || { tail -100 "$bld/make.log"; exit 1; }
for arch in i386 x86_64; do
    mkdir -p "out/isolation/$arch-windows"
    cp "$bld/dlls/ntdll/$arch-windows/ntdll.dll" "out/isolation/$arch-windows/"
    cp "$bld/dlls/shell32/$arch-windows/shell32.dll" "out/isolation/$arch-windows/"
done
mkdir -p out/isolation/x86_64-unix out/isolation/bin
cp "$bld/dlls/ntdll/ntdll.so" out/isolation/x86_64-unix/
cp "$bld/dlls/win32u/win32u.so" "$bld/dlls/winex11.drv/winex11.so" out/isolation/x86_64-unix/
cp "$bld/tools/wine/wine" out/isolation/bin/
cp patches/wine-11.0-app-isolation.patch patches/winehq-60721.patch patches/dllmgr-43.patch patches/dllmgr-44.patch patches/dllmgr-46.patch patches/dllmgr-49.patch patches/dllmgr-52.patch patches/dllmgr-65.patch out/isolation/
printf '%s\n' 'wine-11.0 db11d0fe6a169c457e23d007e20404643d067aa8 + wine-11.0-app-isolation.patch + winehq-60721.patch + dllmgr-43.patch + dllmgr-44.patch + dllmgr-46.patch + dllmgr-49.patch + dllmgr-52.patch + dllmgr-65.patch' > out/isolation/SOURCE.txt
(cd out/isolation && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
