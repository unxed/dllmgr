#!/usr/bin/env bash
# Enable catalog fix winehq-59609 (catalog/fixes/winehq-59609.md; FastStone thumbnail strip)
# for FSViewer.exe only. A stand-in until the dllmgr CLI exists; it uses the tools of
# https://github.com/unxed/fix-it-in-wine (cloned into the work dir, or FIW_TOOLS).
#
# Usage: apply.sh [--exe PATH/FSViewer.exe] [--build]
#        apply.sh --undo
#   WINEPREFIX: the prefix FastStone runs in (default ~/.wine).
#   --exe:   FSViewer.exe to check (default: the first one found in the prefix's drive_c).
#   --build: build the DLL here instead of downloading it (needs the packages listed by
#            fix-it-in-wine's tools/build_one_dll.sh). Also used when the release has no file
#            for your Wine.
#
# The DLL comes from https://github.com/unxed/dllmgr/releases/tag/winehq-59609 for your
# exact `wine --version`, checked against SHA256SUMS. Other programs and the system Wine are
# not changed. Undo: apply.sh --undo.
set -euo pipefail

release=https://github.com/unxed/dllmgr/releases/download/winehq-59609
patch_url=https://raw.githubusercontent.com/unxed/fix-it-in-wine/main/showcases/59609/fix.patch
patch_sha256=4c4e4672a06370e612f9305be7cab7a59c8dd7d8638297b1029831a4d0218295
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
exe="" build=0

while [ $# -gt 0 ]; do
    case $1 in
        --undo) exec python3 "$tools/override.py" undo --prefix "$WINEPREFIX" --exe FSViewer.exe --name comctl32 ;;
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

mkdir -p "$work/release"
dll=$work/release/$file
if [ "$build" = 0 ]; then
    if curl -fsSL -o "$dll" "$release/$file" && curl -fsSL -o "$work/release/SHA256SUMS" "$release/SHA256SUMS"; then
        (cd "$work/release" && grep " $file\$" SHA256SUMS | sha256sum -c --quiet) || { echo "checksum mismatch for $file" >&2; exit 2; }
    else
        echo "no prebuilt $file in the release: building it here"
        build=1
    fi
fi
if [ "$build" = 1 ]; then
    src=$work/src/$tag
    [ -d "$src/.git" ] || git clone -q --depth 1 --branch "$tag" "${FIW_WINE_GIT:-https://gitlab.winehq.org/wine/wine.git}" "$src"
    patch=$work/release/winehq-59609.patch
    curl -fsSL -o "$patch" "$patch_url"
    echo "$patch_sha256  $patch" | sha256sum -c --quiet || { echo "checksum mismatch for the patch" >&2; exit 2; }
    git -C "$src" apply --check "$patch" 2>/dev/null && git -C "$src" apply "$patch"
    git -C "$src" apply --reverse --check "$patch" 2>/dev/null || { echo "the patch does not apply to $tag" >&2; exit 2; }
    dll=$(bash "$tools/build_one_dll.sh" "$tag" "$mod" | grep "/$mod/$arch-windows/")
fi

python3 "$tools/override.py" apply --prefix "$WINEPREFIX" --exe FSViewer.exe --dll "$dll" --name comctl32.dll --slot "$slot"
echo
echo "Done. Start FastStone, open a folder with many images, press F, move the mouse to the top"
echo "of the screen and scroll the strip: the thumbnails must stay drawn."
echo "Undo: $0 --undo"
