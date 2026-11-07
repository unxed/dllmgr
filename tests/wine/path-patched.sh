#!/usr/bin/env bash
# Disposable CI prefix only. The owner's installed DLLs/settings are never used.
set -euo pipefail
export FIW_WORK=$RUNNER_TEMP/path-build FIW_WINE_GIT=https://github.com/wine-mirror/wine.git
export WINEPREFIX=$RUNNER_TEMP/path-fixed-prefix WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
repo=$GITHUB_WORKSPACE
src=$FIW_WORK/src/wine-11.0
out=$RUNNER_TEMP/path-patched
mkdir -p "$out" "$(dirname "$src")"
git clone -q --depth 1 --branch wine-11.0 "$FIW_WINE_GIT" "$src"
test "$(git -C "$src" rev-parse HEAD)" = db11d0fe6a169c457e23d007e20404643d067aa8
wineboot -u >"$out/wineboot.txt" 2>&1
wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d 192 /f
timeout 60 wineserver -w
curl --max-time 90 -fsSL https://www.faststonesoft.net/DN/FSViewer85.zip -o "$out/fs85.zip"
echo "685282a063b91daf4388b84be9e0daf3c5feed4073651137eb9fe9421cf39439  $out/fs85.zip" | sha256sum -c
fixture=$WINEPREFIX/drive_c/dllmgr-path-test
mkdir -p "$fixture"
(cd "$fixture" && python3 "$repo/tests/wine/make-images.py")
sxs=("$WINEPREFIX"/drive_c/windows/winsxs/x86_microsoft.windows.common-controls_6595b64144ccf1df_6.*/comctl32.dll)
test "${#sxs[@]}" -eq 1
sha256sum "${sxs[0]}" >"$out/original.sha256"
undo_needed=0
cleanup() {
    rc=$?
    if [ "$undo_needed" = 1 ]; then
        python3 "$repo/fiw/tools/override.py" undo --prefix "$WINEPREFIX" --exe FSViewer.exe --name comctl32 || rc=1
        sha256sum -c "$out/original.sha256" || rc=1
    fi
    timeout 30 wineserver -k || true
    timeout 30 wineserver -w || rc=1
    exit "$rc"
}
trap cleanup EXIT
for selection in isolated combined; do
    git -C "$src" restore -- dlls/comctl32/listview.c dlls/comctl32_v6/combo.c
    if [ "$selection" = combined ]; then
        for fix in winehq-48872 winehq-59251 winehq-59609 dllmgr-14; do
            git -C "$src" apply "$repo/patches/$fix.patch"
        done
    fi
    git -C "$src" apply "$repo/patches/dllmgr-21.patch"
    bash "$repo/fiw/tools/build_one_dll.sh" wine-11.0 comctl32_v6 >"$out/build-$selection.txt"
    dll=$(grep '/i386-windows/comctl32_v6.dll$' "$out/build-$selection.txt")
    test -f "$dll"
    mkdir "$out/$selection"
    python3 "$repo/fiw/tools/pe_unmark.py" "$dll" "$out/$selection/comctl32_v6-wine-11.0-i386.dll"
    python3 "$repo/fiw/tools/override.py" apply --prefix "$WINEPREFIX" --exe FSViewer.exe --dll "$out/$selection/comctl32_v6-wine-11.0-i386.dll" --name comctl32.dll --slot 'sxs:x86_microsoft.windows.common-controls_6595b64144ccf1df_6.*' >"$out/$selection/install.txt"
    undo_needed=1
    timeout 30 wineserver -k || true
    timeout 30 wineserver -w
    rm -rf "$fixture/FSViewer85"
    unzip -q "$out/fs85.zip" -d "$fixture"
    (cd "$out/$selection" && WINEDEBUG=+loaddll timeout 75 wine "$repo/path-observer.exe" 'C:\dllmgr-path-test\FSViewer85\FSViewer.exe' 'C:\dllmgr-path-test\images\browser\00-landscape.bmp' >observations.txt 2>modules.txt)
    grep -Ei 'loaddll:.*\\comctl32\.dll.*: native' "$out/$selection/modules.txt"
    python3 "$repo/tests/wine/check-path-dropdown.py" "$out/$selection"
    cmp "${sxs[0]}" "$out/$selection/comctl32_v6-wine-11.0-i386.dll"
    python3 "$repo/fiw/tools/override.py" undo --prefix "$WINEPREFIX" --exe FSViewer.exe --name comctl32 >"$out/$selection/undo.txt"
    undo_needed=0
    sha256sum -c "$out/original.sha256" >>"$out/$selection/undo.txt"
    timeout 30 wineserver -k || true
    timeout 30 wineserver -w
    sha256sum "$out/$selection/comctl32_v6-wine-11.0-i386.dll" >"$out/$selection/SHA256SUMS"
done
