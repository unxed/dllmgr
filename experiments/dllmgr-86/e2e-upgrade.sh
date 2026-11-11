#!/usr/bin/env bash
# #86 end-to-end on the headless stand: the owner's flow with a disposable
# prefix and a temporary HOME. Old dllmgr (981e902, runtime v22) fixes
# Photoshop CS2, then `dllmgr update` (from this checkout's update.py, as the
# old dllmgr has none) and `dllmgr upgrade` move it to the current pins.
# Usage: W=<work dir> BASE=<prefix with CS2 installed> e2e-upgrade.sh
# Run inside `scripts/sandbox-stand.sh session`. Never touches the real HOME.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
: "${W:?}" "${BASE:?}"
export HOME=$W/home XDG_DATA_HOME=$W/home/.local/share XDG_CACHE_HOME=$W/cache XDG_STATE_HOME=$W/state
export WINEPREFIX=$W/prefix WINEDLLOVERRIDES='mscoree,mshtml='
mkdir -p "$HOME" "$XDG_CACHE_HOME/dllmgr/downloads"
# Runtime packages from local copies (sha256 checked by dllmgr), no download.
for f in ${RUNTIME_ZIPS:-}; do
    cp -- "$f" "$XDG_CACHE_HOME/dllmgr/downloads/$(sha256sum <"$f" | cut -d' ' -f1)"
done
[ -d "$WINEPREFIX" ] || cp -a -- "$BASE" "$WINEPREFIX"
dllmgr=$HOME/.local/bin/dllmgr
step() { printf '\n===== %s\n' "$*"; }
step "old dllmgr 981e902 (runtime v22)"
python3 "$repo/scripts/update.py" --revision 981e902
step "dllmgr fix photoshop-cs2 (old)"
"$dllmgr" fix photoshop-cs2 --prefix "$WINEPREFIX" | grep -E 'Versions|installed|Warning|trampoline' || true
"$dllmgr" set photoshop-cs2 text=gray contrast=1.5
step "dllmgr update"
python3 "$repo/scripts/update.py"
step "dllmgr upgrade --dry-run"
"$dllmgr" upgrade --dry-run
step "dllmgr upgrade (answer: no)"
echo n | "$dllmgr" upgrade
step "dllmgr upgrade --yes"
"$dllmgr" upgrade --yes
step "dllmgr upgrade (again)"
"$dllmgr" upgrade
step "dllmgr status photoshop-cs2"
"$dllmgr" status photoshop-cs2 --prefix "$WINEPREFIX" | grep -E 'Versions|Settings|trampoline|✓'
wineserver -k 2>/dev/null || true
