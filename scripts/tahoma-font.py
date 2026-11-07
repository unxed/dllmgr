#!/usr/bin/env python3
"""Install/undo the corrected Wine Tahoma Bold in one prefix, without registry edits."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

FONT = Path('drive_c/windows/Fonts/dllmgr-tahomabd.ttf')
NOTICES = Path('drive_c/dllmgr/fonts/tahoma-bold/THIRD-PARTY-NOTICES.txt')
STATE = Path('.dllmgr/tahoma-bold.json')


class Error(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.tahoma-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load(prefix):
    state = json.loads((prefix/STATE).read_text())
    if state.get('format') != 1 or state.get('phase') not in ('pending', 'installed'):
        raise Error('Unrecognized managed font state')
    if set(state.get('files', {})) != {str(FONT), str(NOTICES)}:
        raise Error('Unrecognized managed font paths')
    return state


def unchanged(prefix, state, allow_missing=False):
    for name, digest in state['files'].items():
        path = prefix/name
        if not path.exists() and allow_missing:
            continue
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise Error('Managed font or notices changed outside dllmgr: '+name)


def apply(prefix, font, notices):
    data, license_text = font.read_bytes(), notices.read_bytes()
    if len(data) < 12 or data[:4] != b'\0\1\0\0':
        raise Error('Expected a TrueType font')
    if not license_text.strip():
        raise Error('License notices are required')
    payload = {str(FONT): data, str(NOTICES): license_text}
    hashes = {name: sha(content) for name, content in payload.items()}
    if (prefix/STATE).exists():
        state = load(prefix)
        unchanged(prefix, state)
        if state['phase'] == 'installed' and state['files'] == hashes:
            return 'already installed'
        raise Error('Another managed font build exists; undo it before upgrading')
    if any((prefix/name).exists() for name in payload):
        raise Error('Font target or notices already exist without managed state')
    state = dict(format=1, phase='pending', files=hashes)
    atomic(prefix/STATE, json.dumps(state, indent=2).encode(), 0o600)
    try:
        for name, content in payload.items():
            atomic(prefix/name, content)
        state['phase'] = 'installed'
        atomic(prefix/STATE, json.dumps(state, indent=2).encode(), 0o600)
    except BaseException:
        for name in payload:
            (prefix/name).unlink(missing_ok=True)
        (prefix/STATE).unlink(missing_ok=True)
        raise
    return 'installed'


def undo(prefix):
    state = load(prefix)
    unchanged(prefix, state, allow_missing=True)
    for name in state['files']:
        (prefix/name).unlink(missing_ok=True)
    (prefix/STATE).unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['apply', 'undo', 'status'])
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--font', type=Path)
    parser.add_argument('--notices', type=Path)
    args = parser.parse_args()
    prefix = args.prefix.resolve()
    if not (prefix/'system.reg').is_file():
        parser.error('prefix must already be initialized')
    lock = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.command == 'apply':
            if not args.font or not args.notices:
                parser.error('apply requires --font and --notices')
            print('Corrected Wine Tahoma Bold '+apply(prefix, args.font, args.notices))
            print('Scope: Tahoma Bold in this Wine prefix. Restart Wine applications.')
        elif args.command == 'undo':
            undo(prefix)
            print('Corrected Tahoma removed; original font files were never replaced.')
        else:
            state = load(prefix)
            if state['phase'] != 'installed':
                raise Error('Incomplete font installation; undo it first')
            unchanged(prefix, state)
            print('Corrected Wine Tahoma Bold: ok')
    finally:
        os.close(lock)


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError, KeyError) as error:
        raise SystemExit('dllmgr fonts: '+str(error))
