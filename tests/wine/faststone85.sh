#!/usr/bin/env bash
set -euo pipefail
export WINEPREFIX=$RUNNER_TEMP/fs85-$TEST_DPI WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
wineboot -u
wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
wine reg add 'HKCU\Software\Wine\Fonts' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
wineserver -w
mkdir -p snapshots85
wine --version > snapshots85/environment.txt
printf 'requested_dpi=%s\n' "$TEST_DPI" >> snapshots85/environment.txt
curl -fsSL --retry 3 --max-time 120 https://www.faststonesoft.net/DN/FSViewer85.zip -o fs85.zip
echo '685282a063b91daf4388b84be9e0daf3c5feed4073651137eb9fe9421cf39439  fs85.zip' | sha256sum -c
unzip -q fs85.zip
python3 tests/wine/make-images.py
app=$(winepath -w "$GITHUB_WORKSPACE/FSViewer85/FSViewer.exe")
for action in middle enter draw browser; do
    image=images/white.bmp
    if [ "$action" = browser ]; then image=images/browser/00-landscape.bmp; fi
    image=$(winepath -w "$GITHUB_WORKSPACE/$image")
    mkdir -p "snapshots85/$action"
    (cd "snapshots85/$action" && wine "$GITHUB_WORKSPACE/app-observer.exe" "$app" "$image" "$action" | tee observations.txt)
done
wine "$GITHUB_WORKSPACE/font-probe.exe" > snapshots85/fonts.txt
if [ "$TEST_DPI" = 192 ]; then
    image=$(winepath -w "$GITHUB_WORKSPACE/images/white.bmp")
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
wineserver -k || true
