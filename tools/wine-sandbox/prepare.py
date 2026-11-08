#!/usr/bin/env python3
"""Prepare a user-owned Wine 11.0/Xvfb test environment; never install packages."""
import argparse
import concurrent.futures
import hashlib
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess as sp

HERE = Path(__file__).resolve().parent


def checked(args, **kwargs):
    return sp.run([str(a) for a in args], check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--state', type=Path, default=Path('/workspace/work/wine-sandbox'))
    ap.add_argument('--workspace', type=Path, default=Path('/workspace'))
    args = ap.parse_args()
    state, workspace = args.state.resolve(), args.workspace.resolve()
    if not state.is_relative_to(workspace) or state == workspace:
        ap.error('--state must be a subdirectory of --workspace')
    if platform.machine() != 'x86_64':
        ap.error('this package lock requires an x86_64 Debian 13 host')
    for tool in ['curl', 'dpkg-deb']:
        if not shutil.which(tool):
            ap.error(f'missing host prerequisite: {tool}')
    state.mkdir(parents=True, exist_ok=True)
    state_lock = (state/'run.lock').open('w')
    try:
        fcntl.flock(state_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        ap.error('another job owns this stand; stop it before preparation')
    cache, root = state/'debs', state/'root'
    cache.mkdir(exist_ok=True)
    root.mkdir(exist_ok=True)
    lock = json.loads((HERE/'packages.lock.json').read_text())

    def fetch(pkg):
        target = cache/pkg['file']
        def valid():
            if not target.exists():
                return False
            with target.open('rb') as data:
                return hashlib.file_digest(data, 'sha256').hexdigest() == pkg['sha256']
        if not valid():
            partial = target.with_suffix('.partial')
            checked(['curl', '--fail', '--location', '--silent', '--show-error', '--retry', '2',
                     '--connect-timeout', '30', '--max-time', '600', pkg['url'], '-o', partial])
            if hashlib.sha256(partial.read_bytes()).hexdigest() != pkg['sha256']:
                raise RuntimeError(f"SHA256 mismatch: {pkg['file']}")
            partial.replace(target)
        return pkg, target

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(fetch, lock['packages']))
    # Sequential extraction: packages may contain shared directory entries.
    for pkg, deb in fetched:
        dest = state/'kernel' if pkg['package'].startswith('linux-image-') else root
        checked(['dpkg-deb', '-x', deb, dest])
    # Relocate only the private i386 ELF interpreter; retain pristine loader bytes.
    loader = root/'opt/wine-stable/lib/wine/i386-unix/wine'
    shutil.copy2(loader, loader.with_name('wine.original'))
    checked([root/'usr/bin/patchelf', '--set-interpreter',
             root/'usr/lib/i386-linux-gnu/ld-linux.so.2', loader])
    config = {'state': str(state), 'workspace': str(workspace), 'uid': os.getuid(),
              'gid': os.getgid(), 'kernel': str(next((state/'kernel/boot').glob('vmlinuz-*')))}
    (state/'stand.json').write_text(json.dumps(config, indent=2)+'\n')
    for name in ['guest.py', 'build_initramfs.py', 'run.py', 'packages.lock.json']:
        shutil.copy2(HERE/name, state/name)
    checked(['python3', state/'build_initramfs.py'])
    print(f'Prepared {state}. Run: python3 {state}/run.py --smoke')


if __name__ == '__main__':
    main()
