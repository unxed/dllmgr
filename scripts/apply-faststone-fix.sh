#!/usr/bin/env bash
# Enable catalog fix winehq-59609 (catalog/fixes/winehq-59609.md; FastStone thumbnail strip)
# for FSViewer.exe only. A stand-in until the dllmgr CLI exists; it uses the tools of
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
# exact `wine --version`, checked against SHA256SUMS. Other programs and the system Wine are
# not changed. Undo: apply.sh --undo.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Adapt OEM reg.exe output to UTF-8 for older fix-it-in-wine helpers.
export DLLMGR_WINE=${FIW_WINE:-wine}
export FIW_WINE=$here/wine-reg-utf8.py
export FIW_WINE_ENCODING=utf-8
export PYTHONIOENCODING=utf-8

fix=${DLLMGR_FIX:-winehq-59609}
case $fix in
    winehq-48872|winehq-59251|winehq-59609) fixes=$fix ;;
    faststone) fixes='winehq-48872 winehq-59251 winehq-59609' ;;
    *) echo "unknown fix set: $fix" >&2; exit 2 ;;
esac
release=https://github.com/unxed/dllmgr/releases/download/$fix
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine}
work=${FIW_WORK:-$HOME/.cache/fix-it-in-wine}
if [ -n "${FIW_TOOLS:-}" ]; then
    tools=$FIW_TOOLS
else
    if [ -d "$work/fix-it-in-wine/.git" ]; then
        git -C "$work/fix-it-in-wine" pull -q --ff-only || true
    else
        mkdir -p "$work" && git clone -q --depth 1 https://github.com/unxed/fix-it-in-wine "$work/fix-it-in-wine"
    fi
    tools=$work/fix-it-in-wine/tools
fi
export DLLMGR_TOOLS=$tools
exe="" build=0

while [ $# -gt 0 ]; do
    case $1 in
        --undo) exec python3 "$here/manage-faststone.py" undo --fix "$fix" --prefix "$WINEPREFIX" ;;
        --build) build=1 ;;
        --exe) exe=$2; shift ;;
        *) echo "usage: $0 [--exe PATH/FSViewer.exe] [--build] | --undo" >&2; exit 1 ;;
    esac
    shift
done

[ -f "$WINEPREFIX/system.reg" ] || { echo "no Wine prefix at $WINEPREFIX (set WINEPREFIX)" >&2; exit 2; }
if [ -z "$exe" ]; then
    exe=$(find "$WINEPREFIX/drive_c" -iname FSViewer.exe -print -quit 2>/dev/null || true)
    [ -n "$exe" ] || { echo "FSViewer.exe not found in $WINEPREFIX/drive_c; pass --exe PATH" >&2; exit 2; }
fi
arch=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import pe_unmark; print(pe_unmark.pe_machine(open(sys.argv[2], "rb").read()))' "$tools" "$exe")
case $arch in i386) sx=x86 ;; x86_64) sx=amd64 ;; *) echo "$exe: unsupported architecture $arch" >&2; exit 2 ;; esac
tag=$(wine --version | cut -d' ' -f1)

# A program that asks for common controls 6 in its manifest loads the side-by-side copy from
# winsxs; otherwise comctl32 comes from the system directory. Wine 11 builds v6 as a separate
# module, comctl32_v6, whose winsxs copy is named comctl32.dll.
if grep -a -q 'Microsoft.Windows.Common-Controls' "$exe"; then
    slot="sxs:${sx}_microsoft.windows.common-controls_6595b64144ccf1df_6.*"
    # The file we replace tells which module it is: its export name is comctl32_v6.dll on Wine 11.
    cur=$(find "$WINEPREFIX"/drive_c/windows/winsxs -maxdepth 2 -ipath "*/${sx}_microsoft.windows.common-controls_6595b64144ccf1df_6.*/comctl32.dll" 2>/dev/null)
    [ "$(printf '%s\n' "$cur" | grep -c .)" = 1 ] || { echo "expected one winsxs comctl32.dll, found: ${cur:-none}" >&2; exit 2; }
    mod=$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import pe_unmark; n = pe_unmark.pe_export_name(open(sys.argv[2], "rb").read()) or ""; print(n.lower().removesuffix(".dll"))' "$tools" "$cur")
    case $mod in comctl32|comctl32_v6) ;; *) echo "$cur: unexpected module '$mod'" >&2; exit 2 ;; esac
else
    slot=system mod=comctl32
fi
file=$mod-$tag-$arch.dll
echo "FastStone: $exe ($arch), $tag, comctl32 $([ "$slot" = system ] && echo v5 || echo v6) -> $file"

release_dir=$work/release/$fix
mkdir -p "$release_dir"
dll=$release_dir/$file
if [ "$build" = 0 ]; then
    download=$(mktemp -d "$release_dir/.download.XXXXXX")
    trap 'rm -rf "$download"' EXIT
    if ! curl -fsSL --retry 3 --connect-timeout 15 -o "$download/$file" "$release/$file" ||
       ! curl -fsSL --retry 3 --connect-timeout 15 -o "$download/SHA256SUMS" "$release/SHA256SUMS"; then
        echo "could not download prebuilt $file from $release" >&2
        echo "Retry later, or pass --build to compile locally (requires Wine build packages)." >&2
        exit 2
    fi
    (cd "$download" && awk -v file="$file" '$2 == file {print}' SHA256SUMS | sha256sum -c --quiet) || { echo "checksum mismatch for $file" >&2; exit 2; }
    mv "$download/$file" "$dll"
fi
if [ "$build" = 1 ]; then
    # Each selection has an isolated source/build cache, so individual builds
    # cannot accidentally inherit patches from a previous combined build.
    export FIW_WORK=$work/sets/$fix
    src=$FIW_WORK/src/$tag
    mkdir -p "$(dirname "$src")"
    [ -d "$src/.git" ] || git clone -q --depth 1 --branch "$tag" "${FIW_WINE_GIT:-https://gitlab.winehq.org/wine/wine.git}" "$src"
    for patch_id in $fixes; do
        patch=$here/../patches/$patch_id.patch
        if git -C "$src" apply --check "$patch" 2>/dev/null; then
            git -C "$src" apply "$patch"
        else
            git -C "$src" apply --reverse --check "$patch" 2>/dev/null || { echo "$patch_id does not apply to $tag" >&2; exit 2; }
        fi
    done
    dll=$(bash "$tools/build_one_dll.sh" "$tag" "$mod" | grep "/$mod/$arch-windows/")
fi

python3 "$here/manage-faststone.py" apply --fix "$fix" --prefix "$WINEPREFIX" --dll "$dll" --slot "$slot"
echo
echo "Done. Start FastStone, open a folder with many images, press F, move the mouse to the top"
echo "of the screen and scroll the strip: the thumbnails must stay drawn."
echo "Undo: $here/undo-$fix.sh"
