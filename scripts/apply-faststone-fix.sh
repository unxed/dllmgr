#!/usr/bin/env bash
# Enable catalog fix winehq-59609 (catalog/fixes/winehq-59609.md; FastStone thumbnail strip)
# with an FSViewer.exe load-order rule (legacy shared prefix files). A stand-in until the dllmgr CLI exists; it uses the tools of
# https://github.com/unxed/fix-it-in-wine (cloned into the work dir, or FIW_TOOLS).
#
# Shared apply engine. Public entry points: apply-winehq-*.sh, apply-faststone.sh.
# Usage: apply.sh [--exe PATH/FSViewer.exe] [--build]
#        apply.sh --undo
#   WINEPREFIX: the prefix FastStone runs in (default ~/.wine).
#   --exe:   FSViewer.exe to check (default: the first one found in the prefix's drive_c).
#   --build: build the DLL here instead of downloading it (needs the packages listed by
#            fix-it-in-wine's tools/build_one_dll.sh).
#
# The DLL comes from https://github.com/unxed/dllmgr/releases/tag/winehq-59609 for your
# exact `wine --version`, checked against SHA256SUMS. System/SxS destinations
# are shared by the whole prefix; AppDefaults does NOT isolate their contents.
# Undo: apply.sh --undo.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ui() { python3 "$here/ui.py" "$@"; }
# Adapt OEM reg.exe output to UTF-8 for older fix-it-in-wine helpers.
export DLLMGR_WINE=${FIW_WINE:-wine}
export FIW_WINE=$here/wine-reg-utf8.py
export FIW_WINE_ENCODING=utf-8
export PYTHONIOENCODING=utf-8

fix=${DLLMGR_FIX:-winehq-59609}
fixes=$(python3 "$here/catalog_fixes.py" "$fix") || exit 2
release=https://github.com/unxed/dllmgr/releases/download/$fix
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine}
work=${FIW_WORK:-$HOME/.cache/fix-it-in-wine}
exe="" build=0 undo=0
private_args=()
while [ $# -gt 0 ]; do
    case $1 in
        --undo) undo=1 ;;
        --build) build=1 ;;
        --prefix|--runtime-package|--base-wine|--desktop-entry)
            [ "$#" -ge 2 ] || { echo "$1 needs a value" >&2; exit 2; }
            private_args+=("$1" "$2")
            [ "$1" != --prefix ] || export WINEPREFIX=$2
            shift ;;
        --exe)
            [ "$#" -ge 2 ] || { echo "--exe needs a path" >&2; exit 2; }
            exe=$2; shift ;;
        *) echo "usage: $0 [--exe PATH/FSViewer.exe] [--build] | --undo" >&2; exit 2 ;;
    esac
    shift
done

[ -f "$WINEPREFIX/system.reg" ] || { echo "no Wine prefix at $WINEPREFIX (set WINEPREFIX)" >&2; exit 2; }

# Product installation uses only the private runtime. Retain the old engine
# solely for byte-exact legacy undo and explicitly disposable CI experiments.
if [ "${DLLMGR_UNSAFE_SHARED_RESEARCH:-0}" != 1 ]; then
    args=(--fix "$fix" "${private_args[@]}")
    [ -z "$exe" ] || args+=(--exe "$exe")
    if [ "$undo" = 0 ]; then
        [ "$build" = 0 ] || { echo 'dllmgr: build the private runtime in CI, then install its verified package' >&2; exit 2; }
        exec python3 "$here/private-app.py" install "${args[@]}"
    elif compgen -G "$WINEPREFIX/.dllmgr/apps/faststone-*.json" >/dev/null; then
        exec python3 "$here/private-app.py" uninstall "${args[@]}"
    fi
fi

if [ "$undo" = 0 ]; then
    tag=$("$DLLMGR_WINE" --version | cut -d' ' -f1)
    if [ "${DLLMGR_REQUIRE_PROFILE:-0}" = 1 ]; then
        release=https://github.com/unxed/dllmgr/releases/download/$(python3 "$here/catalog_fixes.py" --release "$fix" "$tag")
        args=()
        [ -z "$exe" ] || args+=("$exe")
        exe=$(python3 "$here/select-faststone.py" "$here/../catalog/index.json" "$WINEPREFIX" "$tag" "${args[@]}")
    elif [ -z "$exe" ]; then
        exe=$(find "$WINEPREFIX/drive_c" -iname FSViewer.exe -print -quit 2>/dev/null || true)
        [ -n "$exe" ] || { echo "FSViewer.exe not found in $WINEPREFIX/drive_c; pass --exe PATH" >&2; exit 2; }
    fi
fi

# Match the Wine helper used by the rollback and native-load checks.
helper=0b37d498ef4fd4b1077421af62974a9b3587e80a
if [ -n "${FIW_TOOLS:-}" ]; then
    tools=$FIW_TOOLS
else
    helper_dir=$work/helpers/$helper
    if [ ! -d "$helper_dir/tools" ]; then
        (
            mkdir -p "$work/helpers"
            checkout=$(mktemp -d "$work/helpers/.checkout.XXXXXX")
            trap 'rm -rf -- "$checkout"' EXIT
            git -C "$checkout" init -q
            git -C "$checkout" fetch -q --depth 1 https://github.com/unxed/fix-it-in-wine.git "$helper"
            git -C "$checkout" checkout -q --detach "$helper"
            mv -T -- "$checkout" "$helper_dir" || [ -d "$helper_dir/tools" ]
        )
    fi
    tools=$helper_dir/tools
fi
export DLLMGR_TOOLS=$tools
if [ "$undo" = 1 ]; then
    ui title
    ui note "Prefix: $WINEPREFIX  ·  Recipe: $fix"
    ui step "Restoring the original DLLs and registry settings"
    if result=$(python3 "$here/manage-faststone.py" undo --fix "$fix" --prefix "$WINEPREFIX"); then
        ui ok "Recipe removed; original files restored."
        [ "${DLLMGR_VERBOSE:-0}" = 1 ] && printf '%s\n' "$result"
        exit 0
    else
        status=$?
        printf '%s\n' "$result" >&2
        exit "$status"
    fi
fi

arch=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import pe_unmark; print(pe_unmark.pe_machine(open(sys.argv[2], "rb").read()))' "$tools" "$exe")
case $arch in i386) sx=x86 ;; x86_64) sx=amd64 ;; *) echo "$exe: unsupported architecture $arch" >&2; exit 2 ;; esac
# A program that asks for common controls 6 in its manifest loads the side-by-side copy from
# winsxs; otherwise comctl32 comes from the system directory. Wine 11 builds v6 as a separate
# module, comctl32_v6, whose winsxs copy is named comctl32.dll.
if [ "$fix" != winehq-48874 ] && grep -a -q 'Microsoft.Windows.Common-Controls' "$exe"; then
    slot="sxs:${sx}_microsoft.windows.common-controls_6595b64144ccf1df_6.*"
    # The file we replace tells which module it is: its export name is comctl32_v6.dll on Wine 11.
    cur=$(find "$WINEPREFIX"/drive_c/windows/winsxs -maxdepth 2 -ipath "*/${sx}_microsoft.windows.common-controls_6595b64144ccf1df_6.*/comctl32.dll" 2>/dev/null)
    [ "$(printf '%s\n' "$cur" | grep -c .)" = 1 ] || { echo "expected one winsxs comctl32.dll, found: ${cur:-none}" >&2; exit 2; }
    mod=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import pe_unmark; n = pe_unmark.pe_export_name(open(sys.argv[2], "rb").read()) or ""; print(n.lower().removesuffix(".dll"))' "$tools" "$cur")
    case $mod in comctl32|comctl32_v6) ;; *) echo "$cur: unexpected module '$mod'" >&2; exit 2 ;; esac
else
    slot=system mod=comctl32
fi
case $fix in
    winehq-48874) modules=gdiplus ;;
    faststone) modules="$mod gdiplus" ;;
    *) modules=$mod ;;
esac
ui title
ui note "FastStone Image Viewer  ·  $arch  ·  Wine ${tag#wine-}"
ui note "Prefix: $WINEPREFIX"
release_dir=$work/release/$fix
mkdir -p "$release_dir"
download=$(mktemp -d "$release_dir/.download.XXXXXX")
trap 'rm -rf "$download"' EXIT
if [ "$build" = 0 ]; then
    ui step "Fetching verified DLLs for $tag"
    if ! curl -fsSL --retry 3 --connect-timeout 15 -o "$download/SHA256SUMS" "$release/SHA256SUMS"; then
        echo "could not download checksums from $release; retry later or pass --build" >&2
        exit 2
    fi
    for module in $modules; do
        file=$module-$tag-$arch.dll
        if ! curl -fsSL --retry 3 --connect-timeout 15 -o "$download/$file" "$release/$file"; then
            echo "could not download $file; retry later or pass --build" >&2
            exit 2
        fi
        (cd "$download" && awk -v file="$file" '$2 == file {print}' SHA256SUMS | sha256sum -c --quiet) || { echo "checksum mismatch for $file" >&2; exit 2; }
    done
else
    ui step "Building patched DLLs for $tag"
    # Separate revisions of the patch series cannot share a patched source tree.
    series=$(for patch_id in $fixes; do sha256sum <"$here/../patches/$patch_id.patch"; done | sha256sum | cut -d' ' -f1)
    export FIW_WORK=$work/sets/$fix/$series
    mkdir -p "$FIW_WORK"
    exec {build_lock}>"$FIW_WORK/build.lock"
    flock "$build_lock"
    src=$FIW_WORK/src/$tag
    mkdir -p "$(dirname "$src")"
    [ -d "$src/.git" ] || git clone -q --depth 1 --branch "$tag" "${FIW_WINE_GIT:-https://gitlab.winehq.org/wine/wine.git}" "$src"
    if [ "${DLLMGR_REQUIRE_PROFILE:-0}" = 1 ] &&
       [ "$(git -C "$src" rev-parse HEAD)" != db11d0fe6a169c457e23d007e20404643d067aa8 ]; then
        echo "unexpected Wine source commit for $tag" >&2
        exit 2
    fi
    for patch_id in $fixes; do
        patch=$here/../patches/$patch_id.patch
        if git -C "$src" apply --check "$patch" 2>/dev/null; then
            git -C "$src" apply "$patch"
        else
            git -C "$src" apply --reverse --check "$patch" 2>/dev/null || { echo "$patch_id does not apply to $tag" >&2; exit 2; }
        fi
    done
    bash "$tools/build_one_dll.sh" "$tag" $modules >"$download/built.txt"
    for module in $modules; do
        dll=$(grep "/$module/$arch-windows/" "$download/built.txt")
        cp "$dll" "$download/$module-$tag-$arch.dll"
    done
fi
python3 - "$download/plan.json" "$download" "$tag" "$arch" "$slot" $modules <<'PLAN'
import json, sys
plan, directory, tag, arch, slot, *modules = sys.argv[1:]
with open(plan, 'w') as output:
    json.dump([dict(dll=f"{directory}/{m}-{tag}-{arch}.dll",
                    name="comctl32.dll" if m.startswith("comctl32") else "gdiplus.dll",
                    slot=slot if m.startswith("comctl32") else "system") for m in modules], output)
PLAN
ui step "Applying the recipe transaction"
if result=$(python3 "$here/manage-faststone.py" apply --fix "$fix" --prefix "$WINEPREFIX" --plan "$download/plan.json"); then
    if [[ $result == *"already enabled"* ]]; then
        ui ok "Recipe already enabled for FSViewer.exe."
    else
        ui ok "Recipe enabled for FSViewer.exe."
    fi
    [ "${DLLMGR_VERBOSE:-0}" = 1 ] && printf '%s\n' "$result"
    ui note "Close Wine apps in this prefix, then wait for wineserver to exit before relaunching FastStone."
    if [ "$fix" = faststone ]; then
        ui note "To undo: dllmgr uninstall faststone"
    else
        ui note "To undo: $here/undo-$fix.sh"
    fi
else
    status=$?
    printf '%s\n' "$result" >&2
    exit "$status"
fi
