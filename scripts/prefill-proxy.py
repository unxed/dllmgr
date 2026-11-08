#!/usr/bin/env python3
"""Install / undo / check the dllmgr-27 prefill proxy for ONE executable.

The proxy (patches/dllmgr-27, `build.sh version|msimg32`) is copied next to
the target exe and that exe alone gets `<dll>=native,builtin` under
HKCU\\Software\\Wine\\AppDefaults\\<exe name>\\DllOverrides. Other programs in
the prefix, and other copies of the same exe name without the file in their
own directory, keep Wine's builtin DLL. Nothing in system32/syswow64, winsxs
or system Wine is touched. The previous override value is restored on undo.

    prefill-proxy.py apply  --prefix P --exe .../Photoshop.exe --proxy version --dll built.dll
    prefill-proxy.py status --prefix P --exe .../Photoshop.exe
    prefill-proxy.py undo   --prefix P --exe .../Photoshop.exe

Uses: #27 FastStone (msimg32), #36 Photoshop CS2 splash (version).
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

PROXIES = ('version', 'msimg32')
STATE_DIR = Path('.dllmgr/prefill')


class Error(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.prefill-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Registry:
    """HKCU access through `wine reg` in the given prefix (replaceable in tests)."""

    def __init__(self, prefix, wine='wine'):
        self.env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG='-all')
        self.wine = wine

    def _reg(self, *args):
        return subprocess.run([self.wine, 'reg', *args], env=self.env, capture_output=True, text=True)

    def get(self, key, name):
        out = self._reg('query', key, '/v', name)
        if out.returncode:
            return None
        for line in out.stdout.splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0] == name and parts[1] == 'REG_SZ':
                return parts[2].strip()
        return None

    def set(self, key, name, value):
        if self._reg('add', key, '/v', name, '/t', 'REG_SZ', '/d', value, '/f').returncode:
            raise Error('wine reg add failed for ' + key)

    def delete(self, key, name):
        self._reg('delete', key, '/v', name, '/f')


def key_for(exe):
    return 'HKCU\\Software\\Wine\\AppDefaults\\' + exe.name + '\\DllOverrides'


def state_path(prefix, exe):
    return prefix / STATE_DIR / (sha(str(exe).encode())[:16] + '.json')


def load(prefix, exe):
    path = state_path(prefix, exe)
    if not path.is_file():
        raise Error('No prefill proxy installed for ' + str(exe))
    state = json.loads(path.read_text())
    if state.get('format') != 1 or state.get('exe') != str(exe) or state.get('proxy') not in PROXIES:
        raise Error('Unrecognized prefill proxy state')
    return state


def apply(prefix, exe, proxy, dll, reg):
    data = dll.read_bytes()
    if data[:2] != b'MZ':
        raise Error('Expected a PE DLL')
    target = exe.parent / (proxy + '.dll')
    path = state_path(prefix, exe)
    if path.exists():
        state = load(prefix, exe)
        if state['sha256'] == sha(data) and target.is_file() and sha(target.read_bytes()) == state['sha256']:
            return 'already installed'
        raise Error('Another prefill proxy build is installed for this exe; undo it first')
    if target.exists():
        raise Error(str(target) + ' already exists and is not managed by dllmgr')
    key = key_for(exe)
    previous = reg.get(key, proxy)
    state = dict(format=1, exe=str(exe), proxy=proxy, target=str(target), sha256=sha(data),
                 override_key=key, previous_override=previous)
    atomic(path, json.dumps(state, indent=2).encode(), 0o600)
    try:
        atomic(target, data)
        reg.set(key, proxy, 'native,builtin')
    except BaseException:
        target.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise
    return 'installed'


def check(prefix, exe, reg):
    state = load(prefix, exe)
    target = Path(state['target'])
    if not target.is_file() or sha(target.read_bytes()) != state['sha256']:
        raise Error('Proxy DLL changed or missing: ' + str(target))
    if reg.get(state['override_key'], state['proxy']) != 'native,builtin':
        raise Error('Load-order override changed outside dllmgr')
    return state


def undo(prefix, exe, reg):
    state = load(prefix, exe)
    target = Path(state['target'])
    if target.exists() and sha(target.read_bytes()) != state['sha256']:
        raise Error('Proxy DLL was changed outside dllmgr; not removing it: ' + str(target))
    target.unlink(missing_ok=True)
    if state['previous_override'] is None:
        reg.delete(state['override_key'], state['proxy'])
    else:
        reg.set(state['override_key'], state['proxy'], state['previous_override'])
    state_path(prefix, exe).unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['apply', 'undo', 'status'])
    parser.add_argument('--prefix', type=Path, default=Path(os.environ.get('WINEPREFIX', str(Path.home() / '.wine'))))
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--proxy', choices=PROXIES)
    parser.add_argument('--dll', type=Path)
    parser.add_argument('--wine', default='wine')
    args = parser.parse_args()
    prefix, exe = args.prefix.resolve(), args.exe.resolve()
    if not (prefix / 'system.reg').is_file():
        parser.error('prefix must already be initialized')
    if not exe.is_file():
        parser.error('exe not found: ' + str(exe))
    reg = Registry(prefix, args.wine)
    lock = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.command == 'apply':
            if not args.proxy or not args.dll:
                parser.error('apply requires --proxy and --dll')
            print('Prefill proxy ' + apply(prefix, exe, args.proxy, args.dll, reg) + ' for ' + exe.name)
            print('Scope: this exe only; shared prefix DLLs and system Wine unchanged.')
        elif args.command == 'undo':
            undo(prefix, exe, reg)
            print('Prefill proxy removed; previous load order restored.')
        else:
            state = check(prefix, exe, reg)
            print('Prefill proxy (' + state['proxy'] + '.dll): ok for ' + exe.name)
    except Error as error:
        raise SystemExit('dllmgr: ' + str(error))
    finally:
        os.close(lock)


if __name__ == '__main__':
    main()
