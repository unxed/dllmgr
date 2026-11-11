#!/usr/bin/env bash
# Install the committed dllmgr runtime from a checkout, for the current user.
# Without a checkout: `dllmgr update` installs the latest commit from GitHub.
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
revision=$(git -C "$source_dir" rev-parse --verify HEAD^{commit})
if [[ ! $revision =~ ^[0-9a-f]{40}$ ]]; then
    echo "dllmgr: expected a GitHub commit SHA" >&2
    exit 1
fi

archive=$(mktemp "${TMPDIR:-/tmp}/dllmgr-install.XXXXXX")
trap 'rm -f -- "$archive"' EXIT
git -C "$source_dir" archive -o "$archive" "$revision" -- dllmgr catalog patches scripts
# The core of the committed revision, so a dirty checkout installs what it names.
core=$(mktemp "${TMPDIR:-/tmp}/dllmgr-core.XXXXXX")
trap 'rm -f -- "$archive" "$core"' EXIT
git -C "$source_dir" show "$revision:scripts/install-version.sh" >"$core"
bash "$core" "$revision" "$archive"
