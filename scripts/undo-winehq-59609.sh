#!/usr/bin/env bash
# Restore the DLL and the previous FSViewer.exe override in WINEPREFIX.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [ "$#" != 0 ]; then
    echo "usage: $0 (set WINEPREFIX to select the prefix)" >&2
    exit 2
fi
exec "$here/apply-winehq-59609.sh" --undo
