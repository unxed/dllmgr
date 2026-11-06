#!/usr/bin/env bash
# Build each source fix and the combined set, then verify real Wine apply/undo.
set -euo pipefail
export FIW_WORK=$RUNNER_TEMP/fiw-build FIW_WINE_GIT=https://github.com/wine-mirror/wine.git
export WINEPREFIX=$RUNNER_TEMP/fixes-prefix WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
tag=$(wine --version | cut -d' ' -f1)
src=$FIW_WORK/src/$tag
mkdir -p results out
git clone -q --depth 1 --branch "$tag" "$FIW_WINE_GIT" "$src"
wine --version
wineserver --version

stop_server() {
    # This prefix is disposable. Wineboot caches KnownDLLs as image sections
    # for the lifetime of the server, so changing the files is not enough.
    # -k returns nonzero when the server has already exited.
    timeout 30s wineserver -k || true
    timeout 30s wineserver -w
}

require_native_load() {
    local module=$1 trace=$2
    if ! grep -iE ":loaddll:.*\\\\$module[.]dll\" .*: native$" "$trace"; then
        echo "expected native $module.dll in $trace" >&2
        return 1
    fi
}

check_controls() {
    local exe=$1 version=$2
    shift 2
    local log="results/$selection-$version" rc=0
    WINEDEBUG=+loaddll,+module wine "./$exe" "$@" 2>"$log-load.txt" | tee "$log.txt" || rc=$?
    require_native_load comctl32 "$log-load.txt"
    return "$rc"
}

build_modules() {
    local dest=$1 dll mod arch
    shift
    bash fiw/tools/build_one_dll.sh "$tag" "$@" > built.txt
    mkdir -p "$dest"
    while read -r dll; do
        mod=$(basename "$(dirname "$(dirname "$dll")")")
        arch=$(basename "$(dirname "$dll")"); arch=${arch%-windows}
        python3 fiw/tools/pe_unmark.py "$dll" "$dest/$mod-$tag-$arch.dll"
    done < built.txt
}

wineboot -u
# Initialization can outlive wineboot.exe; settle it before replacing modules.
timeout 30s wineserver -w || stop_server
for exe in controls.exe controls6.exe; do
    set +e
    extra=; [ "$exe" != controls6.exe ] || extra=--check-icon-cell
    wine "$exe" --check-label --check-wheel --check-position $extra > "results/before-$exe.txt"
    rc=$?
    set -e
    [ "$rc" = 1 ] || { echo "expected known unfixed failures, got $rc"; cat "results/before-$exe.txt"; exit 1; }
done
bundle_fixes=$(python3 scripts/catalog_fixes.py faststone)
for selection in $bundle_fixes faststone; do
    git -C "$src" restore -- dlls/comctl32/listview.c dlls/gdiplus/graphics.c
    fixes=$selection
    [ "$selection" != faststone ] || fixes=$bundle_fixes
    for fix in $fixes; do git -C "$src" apply "$GITHUB_WORKSPACE/patches/$fix.patch"; done
    case $selection in
        winehq-48874) modules=gdiplus ;;
        faststone) modules='comctl32 comctl32_v6 gdiplus' ;;
        *) modules='comctl32 comctl32_v6' ;;
    esac
    build_modules "out/$selection" $modules
    case $selection in
        winehq-48872) checks='--check-label' ;;
        winehq-59251) checks='--check-wheel' ;;
        winehq-59609) checks='--check-position' ;;
        faststone) checks='--check-label --check-wheel --check-position' ;;
        *) checks='' ;;
    esac
    if [[ " $modules " == *" gdiplus "* ]]; then
        cp "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" "$RUNNER_TEMP/original-gdiplus.dll"
        python3 fiw/tools/override.py apply --prefix "$WINEPREFIX" --exe pencil.exe --dll "out/$selection/gdiplus-$tag-x86_64.dll" --name gdiplus.dll
        stop_server
        sha256sum "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" "out/$selection/gdiplus-$tag-x86_64.dll" >"results/$selection-immediate-hashes.txt"
        stat "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" >"results/$selection-stat.txt"
        cp "$WINEPREFIX/fix-it-in-wine/state.json" "results/$selection-state.json"
        wine reg query 'HKCU\Software\Wine\AppDefaults\pencil.exe\DllOverrides' > "results/$selection-registry.txt"
        sha256sum "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" "out/$selection/gdiplus-$tag-x86_64.dll" >"results/$selection-hashes.txt"
        if ! WINEDEBUG=+loaddll,+module wine ./pencil.exe --check >"results/$selection-pencil.txt" 2>"results/$selection-pencil-load.txt"; then
            WINEDLLOVERRIDES='gdiplus=n,b;mscoree,mshtml=' WINEDEBUG=+loaddll wine ./pencil.exe --check >"results/$selection-pencil-env.txt" 2>"results/$selection-pencil-env-load.txt" || true
            cp "$WINEPREFIX/user.reg" "results/$selection-user.reg"
            sha256sum "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" >>"results/$selection-hashes.txt"
            exit 1
        fi
        require_native_load gdiplus "results/$selection-pencil-load.txt"
        cat "results/$selection-pencil.txt"
        python3 fiw/tools/override.py undo --prefix "$WINEPREFIX" --exe pencil.exe --name gdiplus
        cmp "$WINEPREFIX/drive_c/windows/system32/gdiplus.dll" "$RUNNER_TEMP/original-gdiplus.dll"
    fi
    if [ "$selection" != winehq-48874 ]; then
    original=$WINEPREFIX/drive_c/windows/system32/comctl32.dll
    cp "$original" "$RUNNER_TEMP/original-v5.dll"
    sxs=$(find "$WINEPREFIX/drive_c/windows/winsxs" -maxdepth 2 -ipath '*/amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.*/comctl32.dll')
    [ -f "$sxs" ]; cp "$sxs" "$RUNNER_TEMP/original-v6.dll"
    python3 fiw/tools/override.py apply --prefix "$WINEPREFIX" --exe controls.exe --dll "out/$selection/comctl32-$tag-x86_64.dll" --name comctl32.dll
    python3 fiw/tools/override.py apply --prefix "$WINEPREFIX" --exe controls6.exe --dll "out/$selection/comctl32_v6-$tag-x86_64.dll" --name comctl32.dll --slot 'sxs:amd64_microsoft.windows.common-controls_6595b64144ccf1df_6.*'
    stop_server
    wine reg query 'HKCU\Software\Wine\AppDefaults\controls.exe\DllOverrides'
    sha256sum "$original" "out/$selection/comctl32-$tag-x86_64.dll"
    check_controls controls.exe v5 $checks
    case $selection in
        winehq-59251) check_controls controls6.exe v6 $checks --check-icon-wheel-speed ;;
        dllmgr-14) check_controls controls6.exe v6 $checks --check-icon-cell ;;
        faststone) check_controls controls6.exe v6 $checks --check-icon-wheel-speed --check-icon-cell ;;
        *) check_controls controls6.exe v6 $checks ;;
    esac
    python3 fiw/tools/override.py undo --prefix "$WINEPREFIX" --exe controls.exe --name comctl32
    python3 fiw/tools/override.py undo --prefix "$WINEPREFIX" --exe controls6.exe --name comctl32
    cmp "$original" "$RUNNER_TEMP/original-v5.dll"
    cmp "$sxs" "$RUNNER_TEMP/original-v6.dll"
    fi
    stop_server
    printf '%s %s + %s\n' "$tag" "$(git -C "$src" rev-parse HEAD)" "$fixes" > "out/$selection/SOURCE.txt"
    for fix in $fixes; do cp "patches/$fix.patch" "out/$selection/"; done
    (cd "out/$selection" && sha256sum *.dll > SHA256SUMS)
done

