#!/usr/bin/env python3
"""dllmgr update: install the latest dllmgr from GitHub (like `apt update`).

Changes no application: `dllmgr upgrade` re-applies fixes afterwards. Works
without a git checkout: the commit of github.com/unxed/dllmgr main comes from
the GitHub API, its files from raw.githubusercontent.com, each checked against
the git blob SHA-1 of that commit's tree. Installed by scripts/install-version.sh
(the installer core shared with install.sh): ~/.local/lib/dllmgr/<commit>,
atomic switch of ~/.local/bin/dllmgr, older commits kept for rollback
(`dllmgr update --revision OLD`).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = 'unxed/dllmgr'
BRANCH = 'main'
API = 'https://api.github.com/repos/' + REPO
RAW = 'https://raw.githubusercontent.com/' + REPO
TOP = ('dllmgr', 'catalog', 'patches', 'scripts')  # what install.sh installs
SHA = re.compile('[0-9a-f]{40}')
WINE = 'wine-11.0'


class Error(Exception):
    pass


def fetch(url, accept='application/vnd.github+json'):
    request = urllib.request.Request(url, headers={'Accept': accept, 'User-Agent': 'dllmgr-update'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_json(url):
    return json.loads(fetch(url))


def install_dir():
    return Path.home() / '.local/lib/dllmgr'


def launcher():
    return Path.home() / '.local/bin/dllmgr'


def stamp_path():
    """When `dllmgr update` last checked GitHub (read by `dllmgr upgrade`)."""
    return Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'dllmgr/last-update.json'


def write_stamp(revision):
    path = stamp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(dict(time=int(time.time()), revision=revision)) + '\n')
    temp.replace(path)


def read_stamp():
    try:
        data = json.loads(stamp_path().read_text())
        return data if isinstance(data.get('time'), int) else None
    except (OSError, ValueError, AttributeError):
        return None


def installed_revision():
    """Commit ~/.local/bin/dllmgr points to (install.sh layout), or None."""
    link = launcher()
    if not link.is_symlink():
        if link.exists():
            raise Error(str(link) + ' already exists and is not managed by dllmgr')
        return None
    target = Path(os.readlink(link))
    revision = target.parent.name
    if not SHA.fullmatch(revision) or target != install_dir() / revision / 'dllmgr':
        raise Error(str(link) + ' is not managed by dllmgr')
    return revision


def complete(revision):
    root = install_dir() / revision
    record = root / '.dllmgr-revision'
    return (root / 'dllmgr').is_file() and record.is_file() and record.read_text().strip() == revision


def resolve(requested):
    """(commit, tree) of the branch tip or of a requested commit (full or short SHA)."""
    if requested and SHA.fullmatch(requested) and complete(requested):
        return requested, None  # already installed: rollback without network
    if requested and not re.fullmatch('[0-9a-f]{7,40}', requested):
        raise Error('--revision takes a commit SHA')
    if requested:
        local = [p.name for p in install_dir().glob(requested + '*') if SHA.fullmatch(p.name) and complete(p.name)]
        if len(local) == 1:
            return local[0], None
    data = fetch_json(API + '/commits/' + (requested or BRANCH))
    commit, tree = data.get('sha', ''), (data.get('commit') or {}).get('tree', {}).get('sha', '')
    if not SHA.fullmatch(commit) or not SHA.fullmatch(tree):
        raise Error('GitHub returned no commit for ' + (requested or BRANCH))
    return commit, tree


def blob_sha(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def wanted(entries):
    """Files of the installed directories from a recursive tree listing."""
    files = []
    for entry in entries:
        path = entry.get('path', '')
        parts = PurePosixPath(path).parts
        if not parts or parts[0] not in TOP or (parts[0] == 'dllmgr') != (len(parts) == 1):
            continue
        if path.startswith('/') or '..' in parts or '\\' in path:
            raise Error('Unsafe path in the GitHub tree: ' + path)
        if entry.get('type') == 'tree':
            continue
        if entry.get('type') != 'blob' or entry.get('mode') not in ('100644', '100755'):
            raise Error('Unsupported entry in the GitHub tree (link or submodule): ' + path)
        if not SHA.fullmatch(entry.get('sha', '')):
            raise Error('Invalid blob id in the GitHub tree: ' + path)
        files.append(entry)
    if not any(e['path'] == 'dllmgr' and e['mode'] == '100755' for e in files):
        raise Error('The GitHub tree has no dllmgr command; refusing it')
    return files


def download(commit, tree, dest, workers=8):
    """Write the commit's installed files into dest as a tar archive; every
    blob is checked against its SHA-1 in the tree listing."""
    listing = fetch_json(API + '/git/trees/' + tree + '?recursive=1')
    if listing.get('truncated') or listing.get('sha') != tree:
        raise Error('Incomplete tree listing from GitHub')
    files = wanted(listing.get('tree', []))

    def get(entry):
        data = fetch(RAW + '/' + commit + '/' + urllib.parse.quote(entry['path']), accept='*/*')
        if blob_sha(data) != entry['sha']:
            raise Error('Checksum mismatch: ' + entry['path'])
        return entry, data

    print('› Downloading ' + str(len(files)) + ' files of ' + commit[:7] + ' from github.com/' + REPO, flush=True)
    with ThreadPoolExecutor(workers) as pool, tarfile.open(dest, 'w') as archive:
        for entry, data in pool.map(get, files):
            info = tarfile.TarInfo(entry['path'])
            info.size, info.mode, info.mtime = len(data), 0o755 if entry['mode'] == '100755' else 0o644, int(time.time())
            archive.addfile(info, io.BytesIO(data))
    print('  Verified ' + str(len(files)) + ' files (git blob SHA-1 of tree ' + tree[:12] + ')')


def pins(root):
    """What a dllmgr version pins for the user: runtime release and module releases."""
    result = {}
    if root is None:
        return result
    try:
        config = json.loads((root / 'scripts/private-runtime.json').read_text())
        result['Wine runtime'] = (config.get('release') or config.get('url', '?')) + ' (sha256 ' + str(config.get('sha256', '?'))[:12] + ')'
    except (OSError, ValueError):
        result['Wine runtime'] = 'unknown'
    try:
        index = json.loads((root / 'catalog/index.json').read_text())
        for entry in index.get('entries', []):
            if entry.get('kind') != 'bundle':
                continue
            for profile in entry.get('profiles', []):
                if profile.get('wine') == WINE and profile.get('release'):
                    result['modules ' + (entry.get('application') or entry['id'])] = profile['release']
    except (OSError, ValueError, KeyError, AttributeError):
        pass
    return result


def commits_between(old, new):
    try:
        data = fetch_json(API + '/compare/' + old + '...' + new)
        ahead, behind = int(data.get('ahead_by', 0)), int(data.get('behind_by', 0))
    except Exception:  # only a courtesy line
        return ''
    if behind and not ahead:
        return ' (back by ' + str(behind) + ' commits)'
    return ' (' + str(ahead) + ' new commits)' if not behind else ' (' + str(ahead) + ' new, ' + str(behind) + ' dropped)'


def report(old, new):
    before, after = pins(install_dir() / old if old else None), pins(install_dir() / new)
    for key in sorted(after):
        if old is None:
            print('  ' + key + ': ' + after[key])
        elif before.get(key) != after[key]:
            print('  ' + key + ': ' + before.get(key, 'none') + ' -> ' + after[key])
        else:
            print('  ' + key + ': ' + after[key] + ' (unchanged)')
    for key in sorted(set(before) - set(after)):
        print('  ' + key + ': ' + before[key] + ' -> none')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dllmgr update', description=__doc__.split('\n\n')[0])
    parser.add_argument('--revision', help='install this commit instead of the tip of main (rollback)')
    args = parser.parse_args(argv)
    old = installed_revision()
    print('› Checking github.com/' + REPO + ' ' + (args.revision or BRANCH), flush=True)
    new, tree = resolve(args.revision)
    if new == old and complete(new):
        if not args.revision:
            write_stamp(new)
        print('✓ dllmgr is up to date: ' + new[:7])
        return 0
    with tempfile.TemporaryDirectory(prefix='dllmgr-update-') as temp:
        archive = Path(temp) / 'dllmgr.tar'
        if complete(new):
            print('  ' + new[:7] + ' is already in ' + str(install_dir() / new) + ' (no download)')
        else:
            download(new, tree, archive)
        # This dllmgr's installer core; it reads the archive only for a new commit.
        result = subprocess.run(['bash', str(HERE / 'install-version.sh'), new, str(archive)],
                                capture_output=True, text=True)
        print(''.join('  ' + line + '\n' for line in result.stdout.splitlines()), end='')
        print(result.stderr, end='', file=sys.stderr)
        if result.returncode:
            raise Error('installation failed; ' + (old[:7] if old else 'nothing') + ' stays installed')
    if not args.revision:
        write_stamp(new)
    print('✓ dllmgr ' + (old[:7] if old else '(none)') + ' -> ' + new[:7] + (commits_between(old, new) if old else ''))
    report(old, new)
    if old and not (HERE.parent / '.dllmgr-revision').is_file():
        print('  Note: this command ran from ' + str(HERE.parent) + '; ' + str(launcher()) + ' is the updated one.')
    if (install_dir() / new / 'scripts/upgrade.py').is_file():
        print('  Next: dllmgr upgrade (--dry-run shows which fixed apps change). Back: dllmgr update --revision ' +
              (old[:7] if old else 'SHA'))
    elif old:  # an older commit without update/upgrade
        print('  Note: ' + new[:7] + ' has no dllmgr update/upgrade; to come back run ' +
              str(install_dir() / old / 'dllmgr') + ' update')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Error, OSError, ValueError) as error:  # urllib errors are OSError
        print('dllmgr: ' + str(error), file=sys.stderr)
        sys.exit(1)
