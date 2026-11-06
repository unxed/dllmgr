#!/usr/bin/env bash
set -euo pipefail
export WINEPREFIX=$RUNNER_TEMP/fs85-$TEST_DPI WINEDEBUG=-all WINEDLLOVERRIDES='mscoree,mshtml='
wineboot -u
wine reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
wine reg add 'HKCU\Software\Wine\Fonts' /v LogPixels /t REG_DWORD /d "$TEST_DPI" /f
wineserver -w
curl -fsSL --retry 3 --max-time 120 https://www.faststonesoft.net/DN/FSViewer85.zip -o fs85.zip
echo '685282a063b91daf4388b84be9e0daf3c5feed4073651137eb9fe9421cf39439  fs85.zip' | sha256sum -c
unzip -q fs85.zip
python3 tests/wine/make-images.py
mkdir -p images/folder
cp images/white.bmp images/folder/portrait.bmp
app=$(winepath -w "$GITHUB_WORKSPACE/FSViewer85/FSViewer.exe")
image=$(winepath -w "$GITHUB_WORKSPACE/images/white.bmp")
for action in middle enter draw; do
    mkdir -p "snapshots85/$action"
    (cd "snapshots85/$action" && wine "$GITHUB_WORKSPACE/app-observer.exe" "$app" "$image" "$action" | tee observations.txt)
done
wineserver -k || true
