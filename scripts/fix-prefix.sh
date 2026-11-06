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
ui() {
    if [ -f "$here/ui.py" ]; then
        python3 "$here/ui.py" "$@"
    elif [ "$1" != title ]; then
        printf '%s\n' "$2"
    fi
}
verbose=${DLLMGR_VERBOSE:-0}
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
    local tag ready app answer failed=0 report
    tag=$("${FIW_WINE:-wine}" --version | cut -d' ' -f1)
    [ -n "$tag" ] || { echo "dllmgr: cannot run wine" >&2; return 2; }
    local args=()
    [ -z "$exe" ] || args+=(--exe "$exe")
    ui title
    ui note "Prefix: $WINEPREFIX  ·  Wine: $tag"
    report=$(mktemp)
    if ready=$(python3 "$here/detect-apps.py" --ready "${args[@]}" "$WINEPREFIX" "$tag" 2>"$report"); then
        :
    else
        cat "$report" >&2
        rm -f "$report"
        return 2
    fi
    if [ "$verbose" = 1 ]; then
        cat "$report"
    else
        local blocked
        blocked=$(awk -F '\t' '$2 == "unverified" || $2 == "blocked" {n++} END {print n+0}' "$report")
        [ "$blocked" = 0 ] || ui note "$blocked candidate(s) did not match a verified recipe; use --verbose for details."
    fi
    if [ -z "$ready" ]; then
        ui note "Nothing to fix; no verified recipe matches this prefix."
        # Keep failure feedback actionable even when routine scans are compact:
        # show each candidate's path and the exact failed profile key/reason.
        if [ "$verbose" != 1 ]; then
            printf 'dllmgr: verification details:\n' >&2
            awk -F '\t' '$2 == "unverified" || $2 == "blocked" {
                reason = $4
                sub(/^\(/, "", reason)
                sub(/\)$/, "", reason)
                printf "  %s: %s — %s\n", ($3 ? $3 : $1), reason, $1
                found = 1
            }
            END { if (!found) exit 1 }
            ' "$report" >&2 || cat "$report" >&2
        fi
        rm -f "$report"
        return 1
    fi
    rm -f "$report"
    ui ok "Verified recipes: $(printf '%s' "$ready" | tr '\n' ' ' | sed 's/ $//')"
    if [ "$dry" = 1 ]; then
        ui note "Preview only; no files were changed."
        return 0
    fi
    for app in $ready; do
        if [ "$yes" = 0 ]; then
            if [ ! -t 0 ]; then
                echo "dllmgr: to apply, run 'dllmgr fix $app' or add --yes" >&2
                return 1
            fi
            read -r -p "Apply the $app recipe to $WINEPREFIX? [Y/n] " answer || return 1
            case $answer in ''|[Yy]*) ;; *) ui note "Skipped $app."; continue ;; esac
        fi
        if "$here/../dllmgr" fix "$app" "${args[@]}"; then
            :
        else
            failed=1
        fi
    done
    return "$failed"
}

status=0
run || status=$?
if [ "$pause" = 1 ]; then
    read -r -p "Press Enter to close. " _ || true
fi
exit "$status"
