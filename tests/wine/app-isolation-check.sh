#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C.UTF-8 WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
export WINEPREFIX=$RUNNER_TEMP/isolation-prefix WINEARCH=wow64
runtime=$RUNNER_TEMP/isolation-runtime
bld=$RUNNER_TEMP/wine-build
root=$RUNNER_TEMP/isolation-tests
mkdir -p "$runtime" "$root/target Юникод" "$root/other" "$root/private Юникод" results
(cd /opt/wine-stable && sha256sum lib/wine/{i386-windows/ntdll.dll,x86_64-windows/ntdll.dll,x86_64-unix/ntdll.so} bin/wine) > out/isolation/BASE-SHA256SUMS
/opt/wine-stable/bin/wine --version > out/isolation/BASE-VERSION.txt
cp -a /opt/wine-stable/. "$runtime/"
for arch in i386 x86_64; do
    cp "out/isolation/$arch-windows/ntdll.dll" "$runtime/lib/wine/$arch-windows/ntdll.dll"
done
cp out/isolation/x86_64-unix/ntdll.so "$runtime/lib/wine/x86_64-unix/ntdll.so"
cp out/isolation/bin/wine "$runtime/bin/wine"
# The packaged launcher and ntdll are tested together in a copied runtime.
wine=$runtime/bin/wine
export PATH="$runtime/bin:$PATH"
"$wine" wineboot -u
"$runtime/bin/wineserver" -w
for arch in i386 x86_64; do
    compiler=i686-w64-mingw32
    [ "$arch" != x86_64 ] || compiler=x86_64-w64-mingw32
    "$compiler-windres" tests/wine/controls.rc -I tests/wine -O coff -o "$root/$arch.res"
    "$compiler-gcc" -O2 -Wall -municode tests/wine/app-isolation.c "$root/$arch.res" -lcomctl32 -lgdiplus -o "$root/target Юникод/probe-$arch.exe"
done
# Native PE payloads with the Wine builtin marker cleared, leaving export names intact.
python3 - "$bld" "$root" <<'PY'
from pathlib import Path
import sys
build, root = map(Path, sys.argv[1:])
for arch in ('i386', 'x86_64'):
    for module, name in [('gdiplus', 'gdiplus'), ('comctl32_v6', 'comctl32')]:
        data = (build / 'dlls' / module / f'{arch}-windows' / f'{module}.dll').read_bytes()
        marker = b'Wine builtin DLL'
        assert marker in data[:128], (module, arch)
        data = data.replace(marker, b'\0' * len(marker), 1)
        (root / 'private Юникод' / f'{name}-{arch}.dll').write_bytes(data)
PY
hash_shared() {
    find "$WINEPREFIX/drive_c/windows/system32" "$WINEPREFIX/drive_c/windows/syswow64" "$WINEPREFIX/drive_c/windows/winsxs" -type f ! -iname "*.tmp" -print0 | sort -z | xargs -0 sha256sum
}
hash_shared > results/shared-before.sha256
for arch in i386 x86_64; do
    cp "$root/target Юникод/probe-$arch.exe" "$root/target Юникод/other-$arch.exe"
    cp "$root/target Юникод/probe-$arch.exe" "$root/other/probe-$arch.exe"
    export DLLMGR_TARGET_EXE="Z:${root//\//\\}\\target Юникод\\probe-$arch.exe"
    export DLLMGR_GDIPLUS="Z:${root//\//\\}\\private Юникод\\gdiplus-$arch.dll"
    export DLLMGR_COMCTL32="Z:${root//\//\\}\\private Юникод\\comctl32-$arch.dll"
    "$wine" "$root/target Юникод/probe-$arch.exe" private "Z:${root//\//\\}\\other\\probe-$arch.exe" | tee "results/target-child-$arch.txt"
    "$wine" "$root/target Юникод/other-$arch.exe" stock | tee "results/other-exe-$arch.txt"
    "$wine" "$root/other/probe-$arch.exe" stock | tee "results/same-name-$arch.txt"
    DLLMGR_TARGET_EXE= "$wine" "$root/target Юникод/probe-$arch.exe" stock | tee "results/no-rule-$arch.txt"
    if DLLMGR_GDIPLUS='Z:\does-not-exist.dll' "$wine" "$root/target Юникод/probe-$arch.exe" private > "results/missing-$arch.txt" 2>&1; then
        echo 'Missing private DLL unexpectedly fell back'; exit 1
    fi
    if DLLMGR_COMCTL32='relative.dll' "$wine" "$root/target Юникод/probe-$arch.exe" private > "results/relative-$arch.txt" 2>&1; then
        echo 'Relative private DLL unexpectedly fell back'; exit 1
    fi
    if DLLMGR_GDIPLUS="Z:${root//\//\\}\\private Юникод\\..\\private Юникод\\gdiplus-$arch.dll" "$wine" "$root/target Юникод/probe-$arch.exe" private > "results/noncanonical-$arch.txt" 2>&1; then
        echo 'Noncanonical private DLL unexpectedly loaded'; exit 1
    fi
done
hash_shared > results/shared-after.sha256
cmp results/shared-before.sha256 results/shared-after.sha256
printf '%s\n' 'PASS target, Unicode paths, unrelated EXE, same basename elsewhere, inherited child, absent rule, missing DLL, invalid path, immutable shared DLL bytes' | tee results/summary.txt

(cd out/isolation && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
