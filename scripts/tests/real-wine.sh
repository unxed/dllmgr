#!/usr/bin/env bash
# GitHub CI only: exercise real localized registry output in a disposable prefix.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export WINEPREFIX=$RUNNER_TEMP/dllmgr-locale-prefix
export FIW_WORK=$RUNNER_TEMP/dllmgr-locale-cache
export LC_ALL=ru_RU.UTF-8 LANG=ru_RU.UTF-8 WINEDEBUG=-all
export WINEDLLOVERRIDES='mscoree,mshtml='
wineboot -u
wineserver -w
dest=$WINEPREFIX/drive_c/windows/system32/comctl32.dll
cp "$dest" "$RUNNER_TEMP/original-comctl32.dll"
python3 - "$here" "$WINEPREFIX/drive_c/FSViewer.exe" <<'PY'
import pathlib, struct, sys
sys.path.insert(0, sys.argv[1])
from test_apply import pe
data = bytearray(pe())
struct.pack_into('<H', data, 0x64, 0x8664)
pathlib.Path(sys.argv[2]).write_bytes(data)
PY
# Prove that the missing-key output really is CP866, before testing the adapter.
python3 - <<'PY'
import subprocess
r = subprocess.run(['wine', 'reg', 'query',
                    r'HKCU\Software\Wine\AppDefaults\FSViewer.exe\DllOverrides',
                    '/v', 'comctl32'], capture_output=True)
assert r.returncode != 0
assert 'не удалось' in r.stdout.decode('cp866'), repr(r.stdout)
print('Confirmed real Russian OEM registry output:', r.stdout.decode('cp866').strip())
PY
"$here/../apply-winehq-59609.sh"
wine reg query 'HKCU\Software\Wine\AppDefaults\FSViewer.exe\DllOverrides' /v comctl32 | grep native,builtin
"$here/../undo-winehq-59609.sh"
cmp "$dest" "$RUNNER_TEMP/original-comctl32.dll"
if wine reg query 'HKCU\Software\Wine\AppDefaults\FSViewer.exe\DllOverrides' /v comctl32; then
    echo 'override was not removed' >&2
    exit 1
fi
echo 'Real Wine apply/undo restored the original DLL byte for byte and removed the override.'
