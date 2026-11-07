#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export DLLMGR_FIX=dllmgr-21
exec "$here/apply-faststone-fix.sh" --undo "$@"
