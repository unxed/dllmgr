#!/usr/bin/env bash
# Install the committed dllmgr runtime from a checkout, for the current user.
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
revision=$(git -C "$source_dir" rev-parse --verify HEAD^{commit})
if [[ ! $revision =~ ^[0-9a-f]{40}$ ]]; then
    echo "dllmgr: expected a GitHub commit SHA" >&2
    exit 1
fi

install_dir=$HOME/.local/lib/dllmgr
bin_dir=$HOME/.local/bin
version_dir=$install_dir/$revision
launcher=$bin_dir/dllmgr
mkdir -p -- "$install_dir" "$bin_dir"

# Serialize installs so an upgrade never publishes a partly extracted version.
exec 9>"$install_dir/install.lock"
flock 9
if [[ -e $launcher || -L $launcher ]]; then
    current=$(readlink -- "$launcher" || true)
    previous=${current#"$install_dir/"}
    previous=${previous%/dllmgr}
    if [[ ! $previous =~ ^[0-9a-f]{40}$ ||
          $current != "$install_dir/$previous/dllmgr" ||
          ! -f "$install_dir/$previous/.dllmgr-revision" ]]; then
        echo "dllmgr: $launcher already exists and is not managed by this installer" >&2
        exit 1
    fi
fi

stage=''
link_dir=''
entry=''
cleanup() {
    [[ -z $stage ]] || rm -rf -- "$stage"
    [[ -z $link_dir ]] || rm -rf -- "$link_dir"
    [[ -z $entry ]] || rm -f -- "$entry"
}
trap cleanup EXIT

if [[ ! -e $version_dir ]]; then
    stage=$(mktemp -d "$install_dir/.install.XXXXXX")
    git -C "$source_dir" archive "$revision" -- dllmgr catalog patches scripts |
        tar -xf - -C "$stage"
    printf '%s\n' "$revision" >"$stage/.dllmgr-revision"
    [[ -x $stage/dllmgr ]]
    mv -T -- "$stage" "$version_dir"
    stage=''
elif [[ ! -x $version_dir/dllmgr ||
        ! -f $version_dir/.dllmgr-revision ||
        $(<"$version_dir/.dllmgr-revision") != "$revision" ]]; then
    echo "dllmgr: incomplete installation at $version_dir" >&2
    exit 1
fi

link_dir=$(mktemp -d "$bin_dir/.dllmgr.XXXXXX")
ln -s -- "$version_dir/dllmgr" "$link_dir/dllmgr"
mv -Tf -- "$link_dir/dllmgr" "$launcher"
printf 'Installed %s\n' "$launcher"

# A menu entry for one click: `dllmgr fix` for the default prefix, in a terminal.
# Skipped when the path needs Exec escaping (quotes, backquotes, $, \ or %).
apps_dir=${XDG_DATA_HOME:-$HOME/.local/share}/applications
if [[ $launcher != *[\"\`\$\\%]* ]]; then
    mkdir -p -- "$apps_dir"
    entry=$(mktemp "$apps_dir/.dllmgr-fix.XXXXXX")
    printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Fix Windows programs' \
        'Comment=Apply verified Wine fixes to the programs in the default prefix (dllmgr)' \
        "Exec=\"$launcher\" fix --pause" 'Terminal=true' 'Categories=System;' >"$entry"
    chmod 644 -- "$entry"
    mv -f -- "$entry" "$apps_dir/dllmgr-fix.desktop"
    entry=''
    printf 'Added the menu entry "Fix Windows programs"\n'
fi
