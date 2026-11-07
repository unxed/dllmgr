#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
prefix=${WINEPREFIX:-$HOME/.wine}
if [[ ${1:-} = --prefix && $# = 2 ]]; then prefix=$2
elif (($#)); then
    echo 'Usage: undo-winehq-60703.sh [--prefix PATH]' >&2
    exit 2
fi
exec python3 "$here/avif-codec.py" undo --prefix "$prefix"
