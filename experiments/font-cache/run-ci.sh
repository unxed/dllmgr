#!/usr/bin/env bash
# Disposable research runtime only. Never modifies /opt/wine-stable or a user prefix.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${RUNNER_TEMP:?}/font-cache-research
mkdir -p "$out/artifact"
test "$(/opt/wine-stable/bin/wine --version)" = wine-11.0
src=$out/source
build=$out/build
runtime=$out/runtime

git init -q "$src"
git -C "$src" fetch --depth=1 https://github.com/wine-mirror/wine.git db11d0fe6a169c457e23d007e20404643d067aa8
git -C "$src" checkout -q --detach FETCH_HEAD
test "$(git -C "$src" rev-parse HEAD)" = db11d0fe6a169c457e23d007e20404643d067aa8
mkdir "$build"
(cd "$build" && "$src/configure" --enable-archs=i386,x86_64 --without-x --with-freetype --with-fontconfig > "$out/artifact/configure.log" 2>&1)
make -C "$build" -j4 __tooldeps__ dlls/win32u/win32u.so > "$out/artifact/make-stock.log" 2>&1
cp "$build/dlls/win32u/win32u.so" "$out/artifact/stock-win32u.so"
git -C "$src" apply --check "$here/cache4096.patch"
git -C "$src" apply "$here/cache4096.patch"
make -C "$build" -j4 dlls/win32u/win32u.so > "$out/artifact/make-cache.log" 2>&1
cp "$build/dlls/win32u/win32u.so" "$out/artifact/cache4096-win32u.so"
cp -a /opt/wine-stable "$runtime"
x86_64-w64-mingw32-gcc -O2 -finput-charset=UTF-8 "$here/enum-cpu.c" -lgdi32 -o "$out/enum-cpu.exe"
x86_64-w64-mingw32-gcc -O2 -finput-charset=UTF-8 "$here/cache-bench.c" -lgdi32 -o "$out/cache-bench.exe"
for phase in stock cache4096; do
    cp "$out/artifact/$phase-win32u.so" "$runtime/lib/wine/x86_64-unix/win32u.so"
    export WINEPREFIX=$out/prefix-$phase WINELOADER=$runtime/bin/wine WINESERVER=$runtime/bin/wineserver
    export WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
    export PATH=$runtime/bin:$PATH
    xvfb-run -a bash -e -o pipefail -c '
        wineboot -u >"$1/$2-boot.txt" 2>&1
        /usr/bin/time -v wine "$3/enum-cpu.exe" >"$1/$2-enum.txt" 2>"$1/$2-memory.txt"
        wine "$3/cache-bench.exe" >"$1/$2-cache.txt" 2>"$1/$2-cache-errors.txt"
        timeout 60 wineserver -w
    ' bash "$out/artifact" "$phase" "$out"
    grep -F "$runtime/lib/wine/x86_64-unix/win32u.so" "$out/artifact/$phase-enum.txt"
done
python3 "$here/compare.py" "$out/artifact/stock-enum.txt" "$out/artifact/cache4096-enum.txt"
(cd "$out/artifact" && sha256sum *-win32u.so > SHA256SUMS.txt)
printf '%s\n' 'Wine source db11d0fe6a169c457e23d007e20404643d067aa8' "dllmgr $(git -C "$repo" rev-parse HEAD)" > "$out/artifact/source-revisions.txt"
