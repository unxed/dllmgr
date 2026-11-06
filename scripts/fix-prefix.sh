#!/usr/bin/env bash
# `dllmgr fix` without an application: find the programs of installable recipes
# in WINEPREFIX (default ~/.wine) and apply each verified recipe after a yes.
# Usage: fix-prefix.sh [--exe PATH] [--yes] [--dry-run] [--pause]
#   --exe:     also check this executable; if WINEPREFIX is unset and the path is
#              inside a prefix's drive_c, that prefix is used.
#   --yes:     apply without asking.
#   --dry-run: only print what was found.
#   --pause:   wait for Enter at the end (for the desktop entry).
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exe="" yes=0 dry=0 pause=0
while [ $# -gt 0 ]; do
    case $1 in
        --exe)
            [ "$#" -ge 2 ] || { echo "--exe needs a path" >&2; exit 2; }
            exe=$2; shift ;;
        --yes) yes=1 ;;
        --dry-run) dry=1 ;;
        --pause) pause=1 ;;
        *) echo "usage: dllmgr fix [--exe PATH] [--yes] [--dry-run] [--pause]" >&2; exit 2 ;;
    esac
    shift
done
if [ -n "$exe" ] && [ -z "${WINEPREFIX:-}" ] && [[ $exe == */drive_c/* ]]; then
    export WINEPREFIX=${exe%%/drive_c/*}
fi
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine}

# Called as `run || status=$?`, so set -e is off inside: check each step.
run() {
    [ -f "$WINEPREFIX/system.reg" ] || { echo "dllmgr: no Wine prefix at $WINEPREFIX (set WINEPREFIX)" >&2; return 2; }
    local tag ready app answer failed=0
    tag=$("${FIW_WINE:-wine}" --version | cut -d' ' -f1)
    [ -n "$tag" ] || { echo "dllmgr: cannot run wine" >&2; return 2; }
    local args=()
    [ -z "$exe" ] || args+=(--exe "$exe")
    echo "Looking for programs with recipes in $WINEPREFIX ($tag)."
    # The report goes to the terminal (stderr); the ready applications to $ready.
    ready=$(python3 "$here/detect-apps.py" --ready "${args[@]}" "$WINEPREFIX" "$tag") || return 2
    if [ -z "$ready" ]; then
        echo "Nothing to fix: no verified recipe matches this prefix."
        return 1
    fi
    [ "$dry" = 0 ] || return 0
    for app in $ready; do
        if [ "$yes" = 0 ]; then
            if [ ! -t 0 ]; then
                echo "dllmgr: to apply, run 'dllmgr fix $app' or add --yes" >&2
                return 1
            fi
            read -r -p "Apply the $app recipe to $WINEPREFIX? [Y/n] " answer || return 1
            case $answer in ''|[Yy]*) ;; *) echo "Skipped $app."; continue ;; esac
        fi
        "$here/../dllmgr" fix "$app" "${args[@]}" || failed=1
    done
    return "$failed"
}

status=0
run || status=$?
if [ "$pause" = 1 ]; then
    read -r -p "Press Enter to close. " _ || true
fi
exit "$status"
