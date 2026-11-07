#!/usr/bin/env bash
# Add the corrected Wine Tahoma Bold to an existing Wine prefix.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
prefix=${WINEPREFIX:-$HOME/.wine}
font=''
while (($#)); do
    case $1 in
        --prefix|--font)
            (($# >= 2)) || { echo "dllmgr fonts: $1 needs a path" >&2; exit 2; }
            if [[ $1 = --prefix ]]; then prefix=$2; else font=$2; fi
            shift 2 ;;
        -h|--help)
            echo 'Usage: apply-winehq-26037.sh [--prefix PATH] [--font PATH]'
            echo 'Corrects Tahoma Bold for applications in this Wine prefix.'
            echo 'Close Wine applications first. See docs/fonts.md for scope and evidence.'
            echo '--font uses a local build with an adjacent THIRD-PARTY-NOTICES.txt.'
            exit 0 ;;
        *) echo "dllmgr fonts: unknown option: $1" >&2; exit 2 ;;
    esac
done
[[ -f $prefix/system.reg ]] || { echo 'dllmgr fonts: prefix must already be initialized' >&2; exit 2; }
download=''
trap '[[ -z $download ]] || rm -rf -- "$download"' EXIT
if [[ -z $font ]]; then
    download=$(mktemp -d "${TMPDIR:-/tmp}/dllmgr-tahoma.XXXXXX")
    archive=$download/codec.zip
    url=https://github.com/unxed/dllmgr/releases/download/winehq-26037-font-v1/tahoma-bold-winehq-26037-v1.zip
    echo 'Downloading corrected Wine Tahoma Bold…'
    curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 --max-time 180 "$url" -o "$archive"
    python3 - "$archive" <<'PY'
import hashlib
from pathlib import Path
import sys
import zipfile
path = Path(sys.argv[1])
expected = '45e7a7aac4d4b3d79cc7a07c6449b32f6b8acb6c900056fec8e52e92a316764c'
if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit('dllmgr fonts: package checksum mismatch')
with zipfile.ZipFile(path) as archive:
    for name in ('tahomabd.ttf', 'THIRD-PARTY-NOTICES.txt'):
        (path.parent/name).write_bytes(archive.read(name))
PY
    font=$download/tahomabd.ttf
fi
python3 "$here/tahoma-font.py" apply --prefix "$prefix" --font "$font" --notices "$(dirname -- "$font")/THIRD-PARTY-NOTICES.txt"
