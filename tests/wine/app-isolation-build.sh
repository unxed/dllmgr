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
# #66: Wine's Tahoma bitmap strikes are badly spaced; use its hinted outlines
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-66.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-66.patch"
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-69.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-69.patch"
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-36-shape.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-36-shape.patch"
# #68: a window mapped for activation carries the last user time of the process
# (Muffin no longer stacks Photoshop's "Commit the type layer edits?" under the document)
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-68.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-68.patch"
# #69 stem phase: straight stems soft-snapped half way + Viterbi choice of thirds (agg modes; DLLMGR69_STEM=0 off)
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-69-stem.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-69-stem.patch"
# #74: TWAIN source list from a SANE device cache, background refresh (Photoshop start -4.5 s, scanning kept)
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-74-sane.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-74-sane.patch"
# #77: raster "System" served by a TrueType family inside one application (DLLMGR77_SYSTEM=<family>)
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-77.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-77.patch"
# #78/#82: WM_TAKE_FOCUS asks WM_MOUSEACTIVATE; wineserver keeps a non-topmost window non-topmost after a topmost one
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-78.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-78.patch"
# #68: the WM's close request (Alt+F4, close button) counts as user activity of the process
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-68b.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-68b.patch"
# #80: a DPI-unaware thread's drawing on a desktop window DC is scaled to physical pixels
git -C "$src" apply --check "$GITHUB_WORKSPACE/patches/dllmgr-80.patch"
git -C "$src" apply "$GITHUB_WORKSPACE/patches/dllmgr-80.patch"
(cd "$bld" && "$src/configure" --enable-archs=i386,x86_64 --with-x --with-freetype --with-fontconfig > configure.log 2>&1) || { tail -80 "$bld/configure.log"; exit 1; }
make -C "$bld" -j"$(nproc)" __tooldeps__ dlls/ntdll/all tools/wine/wine dlls/gdiplus/all dlls/comctl32_v6/all dlls/win32u/all dlls/winex11.drv/all dlls/shell32/all dlls/sane.ds/all server/wineserver > "$bld/make.log" 2>&1 || { tail -100 "$bld/make.log"; exit 1; }
for arch in i386 x86_64; do
    mkdir -p "out/isolation/$arch-windows"
    cp "$bld/dlls/ntdll/$arch-windows/ntdll.dll" "out/isolation/$arch-windows/"
done
# #65: Photoshop CS2 is 32-bit; only its shell32 is replaced
cp "$bld/dlls/shell32/i386-windows/shell32.dll" out/isolation/i386-windows/
mkdir -p out/isolation/x86_64-unix out/isolation/bin
cp "$bld/dlls/ntdll/ntdll.so" out/isolation/x86_64-unix/
cp "$bld/dlls/win32u/win32u.so" "$bld/dlls/winex11.drv/winex11.so" "$bld/dlls/sane.ds/sane.so" out/isolation/x86_64-unix/
cp "$bld/tools/wine/wine" "$bld/server/wineserver" out/isolation/bin/
# Debug info is not needed at run time and doubled the download (v12 candidate: 22.7 MB)
strip --strip-debug out/isolation/x86_64-unix/*.so out/isolation/bin/wine out/isolation/bin/wineserver
i686-w64-mingw32-strip --strip-debug out/isolation/i386-windows/*.dll
x86_64-w64-mingw32-strip --strip-debug out/isolation/x86_64-windows/*.dll
cp patches/wine-11.0-app-isolation.patch patches/winehq-60721.patch patches/dllmgr-43.patch patches/dllmgr-44.patch patches/dllmgr-46.patch patches/dllmgr-49.patch patches/dllmgr-52.patch patches/dllmgr-65.patch patches/dllmgr-66.patch patches/dllmgr-69.patch patches/dllmgr-36-shape.patch patches/dllmgr-68.patch patches/dllmgr-69-stem.patch patches/dllmgr-74-sane.patch patches/dllmgr-77.patch patches/dllmgr-78.patch patches/dllmgr-68b.patch patches/dllmgr-80.patch out/isolation/
printf '%s\n' 'wine-11.0 db11d0fe6a169c457e23d007e20404643d067aa8 + wine-11.0-app-isolation.patch + winehq-60721.patch + dllmgr-43.patch + dllmgr-44.patch + dllmgr-46.patch + dllmgr-49.patch + dllmgr-52.patch + dllmgr-65.patch + dllmgr-66.patch + dllmgr-69.patch + dllmgr-36-shape.patch + dllmgr-68.patch + dllmgr-69-stem.patch + dllmgr-74-sane.patch + dllmgr-77.patch + dllmgr-78.patch + dllmgr-68b.patch + dllmgr-80.patch' > out/isolation/SOURCE.txt
(cd out/isolation && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
