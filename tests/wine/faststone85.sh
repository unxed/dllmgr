#!/usr/bin/env bash
set -euo pipefail
bundle=${1:-}
work=$PWD
WINEPREFIX=$(mktemp -d "$RUNNER_TEMP/fs85-$TEST_DPI.XXXXXX")
export WINEPREFIX WINEARCH=win64 WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
stop_server() {
    timeout 30s wineserver -k || true
    timeout 30s wineserver -w
}
bundle_applied=0
cleanup() {
    local result=$?
    if [ "$bundle_applied" = 1 ]; then
        python3 "$manager" undo --fix faststone --prefix "$WINEPREFIX" | tee snapshots85/undo.txt || result=1
        sha256sum -c snapshots85/original.sha256 | tee -a snapshots85/undo.txt || result=1
    fi
    stop_server || result=1
    exit "$result"
}
trap cleanup EXIT
wineboot -u
wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
wine reg add 'HKCU\Software\Wine\Fonts' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
timeout 30s wineserver -w || stop_server
mkdir -p snapshots85
version=$(wine --version)
printf '%s\n' "$version" > snapshots85/environment.txt
printf 'requested_dpi=%s\n' "$TEST_DPI" >> snapshots85/environment.txt
curl -fsSL --retry 3 --max-time 120 https://www.faststonesoft.net/DN/FSViewer85.zip -o fs85.zip
echo '685282a063b91daf4388b84be9e0daf3c5feed4073651137eb9fe9421cf39439  fs85.zip' | sha256sum -c
unzip -q fs85.zip
python3 "$GITHUB_WORKSPACE/tests/wine/make-images.py"
app=$(winepath -w "$work/FSViewer85/FSViewer.exe")

if [ -n "$bundle" ]; then
    tag=${version%% *}
    export DLLMGR_TOOLS="$GITHUB_WORKSPACE/fiw/tools"
    manager="$GITHUB_WORKSPACE/scripts/manage-faststone.py"
    (cd "$bundle" && sha256sum -c SHA256SUMS)
    cp "$bundle/SOURCE.txt" snapshots85/source.txt
    controls=("$WINEPREFIX"/drive_c/windows/winsxs/x86_microsoft.windows.common-controls_6595b64144ccf1df_6.*/comctl32.dll)
    test "${#controls[@]}" -eq 1
    sha256sum "${controls[0]}" "$WINEPREFIX/drive_c/windows/syswow64/gdiplus.dll" > snapshots85/original.sha256
    python3 - "$bundle" "$tag" > bundle-plan.json <<'PY'
import json
from pathlib import Path
import sys

bundle, tag = Path(sys.argv[1]), sys.argv[2]
json.dump([
    {"dll": str(bundle / f"comctl32_v6-{tag}-i386.dll"), "name": "comctl32.dll",
     "slot": "sxs:x86_microsoft.windows.common-controls_6595b64144ccf1df_6.*"},
    {"dll": str(bundle / f"gdiplus-{tag}-i386.dll"), "name": "gdiplus.dll", "slot": "system"},
], sys.stdout)
PY
    python3 "$manager" apply --fix faststone --prefix "$WINEPREFIX" --plan bundle-plan.json | tee snapshots85/install.txt
    bundle_applied=1
    stop_server
fi

for action in middle enter draw browser; do
    image=images/white.bmp
    if [ "$action" = browser ]; then image=images/browser/00-landscape.bmp; fi
    image=$(winepath -w "$work/$image")
    mkdir -p "snapshots85/$action"
    (cd "snapshots85/$action" && wine "$GITHUB_WORKSPACE/app-observer.exe" "$app" "$image" "$action" | tee observations.txt)
done
wine "$GITHUB_WORKSPACE/font-probe.exe" > snapshots85/fonts.txt
if [ "$TEST_DPI" = 192 ] && [ -z "$bundle" ]; then
    image=$(winepath -w "$work/images/white.bmp")
    mkdir -p snapshots85/panel-trace
    (
        cd snapshots85/panel-trace
        WINEDEBUG=+timestamp,+pid,+font,+gdi timeout 45s \
            wine "$GITHUB_WORKSPACE/app-observer.exe" "$app" "$image" panel > observations.txt 2> font-full.log
    ) || echo 'Font trace run did not finish cleanly' >&2
    sed -nE '/select_font:Chosen:|font_SelectFont:|SelectObject:|NtGdiExtTextOutW:/p' \
        snapshots85/panel-trace/font-full.log > snapshots85/panel-trace/fonts.txt
    rm snapshots85/panel-trace/font-full.log
fi

if [ -n "$bundle" ]; then
    image=$(winepath -w "$work/images/white.bmp")
    mkdir -p snapshots85/load-trace
    (
        cd snapshots85/load-trace
        WINEDEBUG=+pid,+loaddll timeout 65s \
            wine "$GITHUB_WORKSPACE/app-observer.exe" "$app" "$image" draw > observations.txt 2> modules.log
    )
    python3 "$GITHUB_WORKSPACE/tests/wine/check-faststone-loads.py" \
        snapshots85/load-trace/{observations.txt,modules.log}
fi
