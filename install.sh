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
cleanup() {
    [[ -z $stage ]] || rm -rf -- "$stage"
    [[ -z $link_dir ]] || rm -rf -- "$link_dir"
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
