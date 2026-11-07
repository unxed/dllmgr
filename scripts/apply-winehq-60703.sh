#!/usr/bin/env bash
# Add the experimental x86 AVIF WIC decoder to an existing Wine prefix.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
prefix=${WINEPREFIX:-$HOME/.wine}
dll=''
while (($#)); do
    case $1 in
        --prefix|--dll)
            (($# >= 2)) || { echo "dllmgr AVIF: $1 needs a path" >&2; exit 2; }
            if [[ $1 = --prefix ]]; then prefix=$2; else dll=$2; fi
            shift 2 ;;
        -h|--help)
            echo 'Usage: apply-winehq-60703.sh [--prefix PATH] [--dll PATH]'
            echo 'Adds an experimental AVIF decoder for all 32-bit WIC apps in this prefix.'
            echo 'Close those apps first. See docs/avif.md for supported files and limitations.'
            echo '--dll uses a local build with an adjacent THIRD-PARTY-NOTICES.txt.'
            exit 0 ;;
        *) echo "dllmgr AVIF: unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ -f $prefix/system.reg ]] || { echo 'dllmgr AVIF: prefix must already be initialized' >&2; exit 2; }
download=''
trap '[[ -z $download ]] || rm -rf -- "$download"' EXIT
if [[ -z $dll ]]; then
    download=$(mktemp -d "${TMPDIR:-/tmp}/dllmgr-avif.XXXXXX")
    archive=$download/codec.zip
    url=https://github.com/unxed/dllmgr/releases/download/winehq-60703-v1/dllmgr-avif-winehq-60703-x86.zip
    echo 'Downloading AVIF decoder (x86)…'
    curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 --max-time 180 "$url" -o "$archive"
    python3 - "$archive" <<'PY'
import hashlib
from pathlib import Path
import sys
import zipfile
path = Path(sys.argv[1])
expected = '14a1d7d52693a4696b97614a1cc58372854361ef14c7f346186cc11d2fb2a1f5'
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit('dllmgr AVIF: package checksum mismatch')
with zipfile.ZipFile(path) as archive:
    for name in ('dllmgr-avif.dll', 'THIRD-PARTY-NOTICES.txt'):
        (path.parent/name).write_bytes(archive.read(name))
PY
    dll=$download/dllmgr-avif.dll
fi
python3 "$here/avif-codec.py" apply --prefix "$prefix" --dll "$dll"
