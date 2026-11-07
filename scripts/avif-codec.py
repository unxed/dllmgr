#!/usr/bin/env python3
"""Experimental, reversible x86 AVIF COM registration in one Wine prefix.

This adds an AVIF decoder to 32-bit WIC applications in that prefix. It does
not replace Windows codecs or edit another codec's registration.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

CLSID = '{13B0A525-1176-4B40-8134-D72A67B16BE8}'
CATEGORY = '{7ED96837-96F0-4812-B211-F13C24117ED3}'
VENDOR = '{E2491A3D-B71A-4C4D-85D1-C8DAFB6AF011}'
CONTAINER = '{E1E62521-6787-405B-A339-500715B5763F}'
BGRA = '{6FDDC324-4E03-4BFE-B185-3D77768DC90F}'
ROOTS = (rf'HKLM\Software\Classes\CLSID\{CLSID}',
         rf'HKLM\Software\Classes\CLSID\{CATEGORY}\Instance\{CLSID}')
STATE = Path('.dllmgr/avif-codec.json')
DLL = Path('drive_c/dllmgr/codecs/avif/dllmgr-avif.dll')


class Error(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.avif-')
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def registration():
    root, instance = [s.replace('HKLM', 'HKEY_LOCAL_MACHINE', 1) for s in ROOTS]
    rows = ['Windows Registry Editor Version 5.00', '', f'[{root}]']
    values = {'FriendlyName': 'dllmgr AVIF decoder', 'Author': 'dllmgr contributors',
              'Vendor': VENDOR, 'ContainerFormat': CONTAINER, 'Version': '0.1.0',
              'SpecVersion': '1.0.0.0', 'MimeTypes': 'image/avif', 'FileExtensions': '.avif'}
    rows += [f'"{key}"="{value}"' for key, value in values.items()]
    rows += ['"SupportAnimation"=dword:00000000', '"SupportMultiframe"=dword:00000000',
             '"SupportChromakey"=dword:00000000', '"SupportLossless"=dword:00000001', '',
             f'[{root}\\InprocServer32]', '@="C:\\\\dllmgr\\\\codecs\\\\avif\\\\dllmgr-avif.dll"',
             '"ThreadingModel"="Both"', '', f'[{root}\\Formats\\{BGRA}]', '']
    for i, signature in enumerate((b'ftypavif', b'ftypavis')):
        rows += [f'[{root}\\Patterns\\{i}]', '"Position"=hex(b):04,00,00,00,00,00,00,00',
                 '"Length"=dword:00000008', '"Pattern"=hex:'+','.join(f'{c:02x}' for c in signature),
                 '"Mask"=hex:ff,ff,ff,ff,ff,ff,ff,ff', '"EndOfStream"=dword:00000000', '']
    rows += [f'[{instance}]', f'"CLSID"="{CLSID}"', '"FriendlyName"="dllmgr AVIF decoder"', '']
    return '\r\n'.join(rows).encode('utf-16')


class WineRegistry:
    def __init__(self, prefix):
        self.env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG='-all')
        self.wine = os.environ.get('DLLMGR_WINE', 'wine')

    def call(self, *args):
        try:
            return subprocess.run([self.wine, 'reg', *args], env=self.env,
                                  capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise Error(str(error)) from error

    @staticmethod
    def normalized(key):
        return key.replace('HKLM', 'HKEY_LOCAL_MACHINE', 1).replace('HKCR', 'HKEY_CLASSES_ROOT', 1).casefold()

    def exists(self, key):
        result = self.call('query', key, '/reg:32')
        if not result.returncode:
            return True
        if '\\' not in key:
            raise Error('Cannot query registry root '+key)
        parent = key.rsplit('\\', 1)[0]
        if not self.exists(parent):
            return False
        result = self.call('query', parent, '/reg:32')
        if result.returncode:
            raise Error('Cannot query registry parent '+parent)
        lines = result.stdout.decode('utf-8', errors='replace').splitlines()
        if any(self.normalized(line.strip()) == self.normalized(key) for line in lines):
            raise Error('Registry key exists but cannot be read: '+key)
        return False

    def snapshot(self, key):
        if not self.exists(key):
            return None
        with tempfile.TemporaryDirectory(prefix='dllmgr-avif-') as temp:
            path = Path(temp)/'export.reg'
            result = self.call('export', key, 'Z:'+str(path).replace('/', '\\'), '/y', '/reg:32')
            if result.returncode or not path.is_file():
                raise Error('Cannot export registry key '+key)
            return sha(path.read_bytes().decode('utf-16').replace('\r\n', '\n').encode('utf-8'))

    def install(self):
        with tempfile.TemporaryDirectory(prefix='dllmgr-avif-') as temp:
            path = Path(temp)/'install.reg'; path.write_bytes(registration())
            result = self.call('import', 'Z:'+str(path).replace('/', '\\'), '/reg:32')
            if result.returncode:
                raise Error('Wine could not import the AVIF registration')

    def remove(self):
        for root in reversed(ROOTS):
            if self.exists(root) and self.call('delete', root, '/f', '/reg:32').returncode:
                raise Error('Cannot remove owned registry tree '+root)


def validate_state(state):
    if state.get('format') != 1 or state.get('dll') != str(DLL):
        raise Error('Unrecognized AVIF state; refusing to change it')


def undo(prefix, registry):
    path = prefix/STATE
    if not path.exists():
        raise Error('The managed AVIF codec is not installed')
    state = json.loads(path.read_text()); validate_state(state)
    target = prefix/DLL
    if target.exists() and sha(target.read_bytes()) != state['sha256']:
        raise Error('AVIF DLL changed outside dllmgr; nothing removed')
    if state['phase'] == 'installed':
        if [registry.snapshot(root) for root in ROOTS] != state['registry']:
            raise Error('AVIF registration changed outside dllmgr; nothing removed')
    registry.remove()
    target.unlink(missing_ok=True)
    path.unlink()


def apply(prefix, source, registry):
    path, target = prefix/STATE, prefix/DLL
    data = source.read_bytes()
    if len(data) < 64 or data[:2] != b'MZ':
        raise Error('Expected an x86 PE DLL')
    offset = struct.unpack_from('<I', data, 60)[0]
    if offset+24 > len(data) or data[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H', data, offset+4)[0] != 0x14c:
        raise Error('Expected an x86 PE DLL')
    digest = sha(data)
    if path.exists():
        state = json.loads(path.read_text()); validate_state(state)
        if state['phase'] == 'installed' and state['sha256'] == digest and target.exists() and sha(target.read_bytes()) == digest and [registry.snapshot(k) for k in ROOTS] == state['registry']:
            return 'already installed'
        raise Error('Existing AVIF state differs; undo it before installing another build')
    if target.exists():
        raise Error('The codec target exists without managed state')
    merged = [root.replace('HKLM\\Software\\Classes', 'HKCR', 1) for root in ROOTS]
    if any(registry.exists(root) for root in (*ROOTS, *merged)):
        raise Error('Decoder registration already exists; refusing to overwrite it')
    state = dict(format=1, phase='pending', dll=str(DLL), sha256=digest, registry=[])
    atomic(path, json.dumps(state, indent=2).encode())
    try:
        atomic(target, data, 0o644)
        registry.install()
        state.update(phase='installed', registry=[registry.snapshot(root) for root in ROOTS])
        if any(value is None for value in state['registry']):
            raise Error('AVIF registration was not created')
        atomic(path, json.dumps(state, indent=2).encode())
    except BaseException:
        registry.remove(); target.unlink(missing_ok=True); path.unlink(missing_ok=True)
        raise
    return 'installed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['apply', 'undo', 'status'])
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--dll', type=Path)
    args = parser.parse_args(); prefix = args.prefix.resolve()
    if not (prefix/'system.reg').is_file():
        parser.error('prefix must already be initialized')
    registry = WineRegistry(prefix)
    lock = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.command == 'apply':
            if not args.dll: parser.error('apply requires --dll')
            print('AVIF codec '+apply(prefix, args.dll, registry))
            print('Scope: 32-bit WIC applications in this Wine prefix.')
        elif args.command == 'undo':
            undo(prefix, registry); print('AVIF codec removed; original registration absence restored.')
        else:
            state = json.loads((prefix/STATE).read_text()); validate_state(state)
            good = state['phase'] == 'installed' and (prefix/DLL).is_file() and sha((prefix/DLL).read_bytes()) == state['sha256'] and [registry.snapshot(root) for root in ROOTS] == state['registry']
            if not good: raise Error('AVIF installation is incomplete or changed')
            print('AVIF codec: ok')
    finally:
        os.close(lock)


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError, KeyError) as error:
        raise SystemExit('dllmgr AVIF: '+str(error))
