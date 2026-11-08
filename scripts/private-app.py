#!/usr/bin/env python3
"""Install and launch exact-path application fixes without shared DLL replacement."""
import argparse
import importlib.util
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import json
import locale
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import catalog_fixes
from ui import Progress
from private_runtime import Error, assemble, digest, overlay_for, package_manifest, valid_sha, verify

EXE_SHA = '05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621'
STATE = Path('.dllmgr/apps')
HERE = Path(__file__).resolve().parent
RULES = ('DLLMGR_TARGET_EXE', 'DLLMGR_COMCTL32', 'DLLMGR_GDIPLUS')
# #27 trampoline: proxy shipped in the runtime package (checksummed by its
# manifest); next to FSViewer.exe it relaunches stock-Wine starts through
# `dllmgr run faststone` (patches/dllmgr-27/README.md).
TRAMPOLINE_MEMBER = 'dllmgr-27/msimg32.dll'
_spec = importlib.util.spec_from_file_location('prefill_proxy', HERE / 'prefill-proxy.py')
prefill_proxy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prefill_proxy)


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.dllmgr-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def save(path, data):
    atomic(path, (json.dumps(data, indent=2, sort_keys=True) + '\n').encode())


@contextmanager
def locked(prefix):
    fd = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def winpath(prefix, path):
    path = path.resolve(strict=True)
    drives = prefix / 'dosdevices'
    # Prefer C: to Z: for the same object; the selected spelling is persisted
    # and used both as image launch argument and loader rule.
    for drive in sorted(drives.iterdir(), key=lambda p: (p.name != 'c:', p.name)):
        if not re.fullmatch('[a-zA-Z]:', drive.name) or not drive.is_dir():
            continue
        try:
            relative = path.relative_to(drive.resolve(strict=True))
            return drive.name.upper() + '\\' + str(relative).replace('/', '\\')
        except ValueError:
            pass
    raise Error('Executable/DLL is not reachable through a prefix drive: ' + str(path))


def select(prefix, requested):
    if platform.machine() != 'x86_64' or '#arch=win64' not in (prefix / 'system.reg').read_text(errors='replace'):
        raise Error('This verified profile requires x86-64 Linux and a win64 prefix')
    if requested:
        exe = requested.resolve(strict=True)
    else:
        copies = sorted({p.resolve() for p in (prefix / 'drive_c').rglob('*')
                         if p.name.casefold() == 'fsviewer.exe' and p.is_file()})
        if len(copies) != 1:
            raise Error('Pass --exe to select exactly one FastStone installation')
        exe = copies[0]
    if exe.name.casefold() != 'fsviewer.exe' or digest(exe) != EXE_SHA:
        raise Error('Only the verified FastStone 8.5 x86 executable is supported')
    return exe


def verify_prefix(prefix, base):
    # Do not let a private Wine bootstrap/update shared prefix core DLLs.
    # Initialisation and version upgrades must happen with stock Wine first.
    for directory, arch in [('system32', 'x86_64'), ('syswow64', 'i386')]:
        if digest(prefix / 'drive_c/windows' / directory / 'ntdll.dll') != digest(base / 'lib/wine' / (arch + '-windows') / 'ntdll.dll'):
            raise Error('Prefix does not match stock Wine11; initialise/update it with stock Wine first')
    timestamp = (prefix / '.update-timestamp').read_text().strip()
    if timestamp != str(int((base / 'share/wine/wine.inf').stat().st_mtime)):
        raise Error('Prefix needs a stock-Wine update before private runtime launch')


def legacy_guard(prefix):
    path = prefix / 'fix-it-in-wine/state.json'
    if path.exists():
        state = json.loads(path.read_text())
        if not isinstance(state, dict) or not isinstance(state.get('entries'), list):
            raise Error('Invalid legacy DLL journal; archive and repair it before installing private fixes')
        if any(e.get('exe', '').casefold() == 'fsviewer.exe' for e in state['entries']):
            raise Error('Legacy shared FastStone replacements remain. Restore them with their original verified backups first; see docs/app-isolation.md')
    # Do not silently delete app-local native DLLs installed by another tool.


def app_id(target):
    return 'faststone-' + hashlib.sha256(target.casefold().encode()).hexdigest()[:20]


def read_state(prefix, exe=None):
    paths = sorted((prefix / STATE).glob('faststone-*.json'))
    if exe:
        paths = [prefix / STATE / (app_id(winpath(prefix, exe)) + '.json')]
    if len(paths) != 1 or not paths[0].is_file():
        raise Error('Select one installed private FastStone profile with --exe')
    path = paths[0]
    if path.is_symlink():
        raise Error('Refusing a symlink ownership journal')
    state = json.loads(path.read_text())
    if (state.get('schema') != 1 or state.get('prefix') != str(prefix)
            or state.get('id') != path.stem or app_id(state.get('target', '')) != path.stem
            or state.get('phase') != 'installed' or not valid_sha(state.get('exe_sha256'))):
        raise Error('Invalid private application journal; no files changed')
    return path, state


def checked_files(prefix, state):
    generation = state.get('generation', '')
    if not re.fullmatch('[0-9a-f]{64}', generation):
        raise Error('Invalid private generation')
    directory = prefix / 'drive_c/dllmgr/apps' / state['id'] / generation
    if directory.resolve() != directory.absolute():
        raise Error('Private module directory must not contain symlinks')
    expected = state.get('files')
    if not isinstance(expected, dict) or not expected or not set(expected) <= {'comctl32.dll', 'gdiplus.dll'}:
        raise Error('Invalid private module journal')
    for name, checksum in expected.items():
        if not valid_sha(checksum) or (directory / name).is_symlink() or digest(directory / name) != checksum:
            raise Error('Private DLL changed: ' + name)
    if {p.name for p in directory.iterdir()} != set(expected):
        raise Error('Private DLL directory contains unowned files')
    return directory


def download(url, dest, checksum=None, label=None):
    with urllib.request.urlopen(url, timeout=60) as response, dest.open('wb') as stream:
        bar = Progress(label, int(response.headers.get('Content-Length') or 0)) if label else None
        for block in iter(lambda: response.read(256 * 1024), b''):
            stream.write(block)
            if bar:
                bar.update(len(block))
        if bar:
            bar.close()
    if checksum and digest(dest) != checksum:
        raise Error('Download checksum mismatch: ' + dest.name)


def patched_modules(package):
    try:
        return ', '.join(sorted('/'.join(Path(dest).parts[-2:]) for dest in overlay_for(package_manifest(package)).values()))
    except (Error, KeyError, ValueError, zipfile.BadZipFile):
        return 'unknown (package without a readable manifest)'


def runtime_release(requested):
    """Human-readable runtime origin: release tag of the pin, or a local package."""
    if requested:
        return 'local package ' + str(requested)
    url = json.loads((HERE / 'private-runtime.json').read_text()).get('url', '')
    return url.split('/download/', 1)[-1].split('/', 1)[0] if '/download/' in url else url


def dllmgr_version():
    try:
        return subprocess.check_output(['git', '-C', str(HERE.parent), 'log', '-1', '--format=%h %cs'],
                                       text=True, stderr=subprocess.DEVNULL).strip() or 'unknown'
    except (OSError, subprocess.SubprocessError):
        return 'unknown (' + str(HERE.parent) + ' is not a readable git checkout)'


def print_versions(state):
    print('  Versions: dllmgr ' + dllmgr_version() + ' · runtime ' +
          state.get('runtime_release', 'unknown (installed by an older dllmgr)') +
          ' (sha256 ' + state.get('package_sha256', '?')[:12] + ') · modules ' + str(state.get('release', '?')))


def runtime_package(requested, temp):
    if requested:
        return requested.resolve(strict=True)
    config = json.loads((HERE / 'private-runtime.json').read_text())
    if not valid_sha(config.get('sha256')):
        raise Error('Private runtime release is not pinned yet; refusing legacy shared installation')
    path = temp / 'runtime.zip'
    download(config['url'], path, config['sha256'],
             'Downloading Wine runtime ' + runtime_release(None) + ' from github.com/unxed/dllmgr')
    return path


def modules(fix, temp):
    fixes = catalog_fixes.resolve(fix)
    index = catalog_fixes.load_index()
    names = set()
    for entry in index:
        if entry['id'] in fixes:
            names.update(entry.get('dlls', []))
    names = {'comctl32_v6' if n == 'comctl32' else n for n in names}
    if not names or not names <= {'comctl32_v6', 'gdiplus'}:
        raise Error('Unsupported private recipe modules')
    release = catalog_fixes.release(fix, 'wine-11.0', index)
    url = 'https://github.com/unxed/dllmgr/releases/download/' + release + '/'
    sums = temp / 'SHA256SUMS'
    download(url + 'SHA256SUMS', sums)
    checksums = {}
    for line in sums.read_text().splitlines():
        checksum, filename = line.split()
        if filename in checksums or not valid_sha(checksum):
            raise Error('Invalid release checksums')
        checksums[filename] = checksum
    result = {}
    for module in sorted(names):
        name = module + '-wine-11.0-i386.dll'
        if name not in checksums:
            raise Error('No verified prebuilt DLL: ' + name)
        path = temp / name
        download(url + name, path, checksums[name], 'Downloading ' + name + ' (release ' + release + ')')
        raw = bytearray(path.read_bytes())
        if raw[:2] != b'MZ' or len(raw) < 96:
            raise Error('Invalid PE payload')
        # A native-only override must not retain Wine's builtin placeholder mark.
        field = bytes(raw[0x40:0x60])
        if field.startswith(b'Wine placeholder DLL'):
            raise Error('Refusing a Wine placeholder DLL')
        if field == b'Wine builtin DLL'.ljust(32, b'\0'):
            raw[0x40:0x60] = bytes(32)
        result['comctl32.dll' if module.startswith('comctl32') else 'gdiplus.dll'] = bytes(raw)
    return release, result


def quote_desktop(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def desktop_content(prefix, exe):
    launcher = Path.home() / '.local/bin/dllmgr'
    command = ' '.join(quote_desktop(x) for x in (launcher, 'run', 'faststone', '--prefix', prefix, '--exe', exe)) + ' -- %F'
    return ('[Desktop Entry]\nType=Application\nName=FastStone Image Viewer (dllmgr)\n'
            'Comment=FastStone with application-private Wine fixes\nExec=' + command + '\n'
            'Terminal=false\nStartupWMClass=fsviewer.exe\nMimeType=image/jpeg;image/png;image/webp;image/avif;\n').encode()


def routed_desktop(original, desired):
    if original is None or b'[Desktop Entry]' not in original:
        return desired
    command = next(line for line in desired.decode().splitlines() if line.startswith('Exec='))
    lines = original.decode('utf-8').splitlines(keepends=True)
    output, section, wrote = [], False, False
    for line in lines:
        if line.strip().startswith('['):
            if section and not wrote:
                output.append(command + '\n')
                wrote = True
            section = line.strip() == '[Desktop Entry]'
        if section and line.startswith('Exec='):
            output.append(command + ('\r\n' if line.endswith('\r\n') else '\n'))
            wrote = True
        else:
            output.append(line)
    if section and not wrote:
        if output and not output[-1].endswith('\n'):
            output.append('\n')
        output.append(command + '\n')
    return ''.join(output).encode('utf-8')


def install(args, prefix):
    exe = select(prefix, args.exe)
    target = winpath(prefix, exe)
    ident = app_id(target)
    state_path = prefix / STATE / (ident + '.json')
    if state_path.parent.resolve() != state_path.parent.absolute():
        raise Error('Ownership directory must not contain symlinks')
    legacy_guard(prefix)
    for name in ('gdiplus.dll', 'comctl32.dll'):
        if (exe.parent / name).exists():
            raise Error('App-local ' + name + ' exists; archive/restore it with its original tool first')
    old = None
    if state_path.exists():
        _, old = read_state(prefix, exe)
        checked_files(prefix, old)
    base = args.base_wine.resolve(strict=True)
    if subprocess.check_output([str(base / 'bin/wine'), '--version'], text=True).strip() != 'wine-11.0':
        raise Error('Only Wine 11.0 is supported')
    verify_prefix(prefix, base)
    cache = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'dllmgr/runtimes'
    with tempfile.TemporaryDirectory(prefix='dllmgr-private-') as directory:
        temp = Path(directory)
        print('› Target: ' + target + ' · prefix ' + str(prefix) + ' · base wine-11.0 at ' + str(base))
        print('› Runtime: ' + runtime_release(args.runtime_package))
        package = runtime_package(args.runtime_package, temp)
        runtime = assemble(package, base, cache, Progress)
        print('  Runtime ready: ' + str(runtime))
        print('  Patched Wine modules in it: ' + patched_modules(package))
        release, payloads = modules(args.fix, temp)
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
        generation = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        dest = prefix / 'drive_c/dllmgr/apps' / ident / generation
        if dest.exists():
            test_state = dict(id=ident, generation=generation, files=hashes)
            checked_files(prefix, test_state)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='.modules-', dir=dest.parent))
            try:
                for name, data in payloads.items():
                    (stage / name).write_bytes(data)
                stage.rename(dest)
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
        owned = copy.deepcopy(old.get('desktops', [])) if old else []
        default_desktop = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'applications' / ('dllmgr-' + ident + '.desktop')
        desktops = [default_desktop, *args.desktop_entry]
        template = desktop_content(prefix, exe)
        outputs = {}
        for path in desktops:
            path = path.absolute()
            existing = next((d for d in owned if d['path'] == str(path)), None)
            if existing:
                if not path.is_file() or digest(path) != existing['installed_sha256']:
                    raise Error('Managed desktop entry changed: ' + str(path))
            else:
                if path.is_symlink():
                    raise Error('Refusing a symlink desktop entry')
                existing = dict(path=str(path), before_hex=path.read_bytes().hex() if path.exists() else None)
                owned.append(existing)
            original = bytes.fromhex(existing['before_hex']) if existing.get('before_hex') is not None else (existing['before'].encode() if existing.get('before') is not None else None)
            desired = routed_desktop(original, template)
            outputs[path] = desired
            existing['installed_sha256'] = hashlib.sha256(desired).hexdigest()
        state = dict(schema=1, phase='installed', id=ident, prefix=str(prefix), exe=str(exe),
                     target=target, exe_sha256=EXE_SHA, fix=args.fix, release=release,
                     generation=generation, files=hashes, runtime=str(runtime), base=str(base),
                     package_sha256=digest(package), desktops=owned,
                     runtime_release=runtime_release(args.runtime_package))
        changes = [dict(path=str(p.absolute()),
                        before_hex=p.read_bytes().hex() if p.exists() else None,
                        after_sha256=hashlib.sha256(outputs[p.absolute()]).hexdigest()) for p in desktops]
        pending = dict(state, phase='pending', transaction=dict(previous=old, desktops=changes))
        save(state_path, pending)
        try:
            for path in desktops:
                atomic(path.absolute(), outputs[path.absolute()])
            save(state_path, state)
        except BaseException:
            recover(prefix, state_path)
            raise
        for name, checksum in sorted(hashes.items()):
            print('  Private DLL: ' + name + ' (sha256 ' + checksum[:12] + ') in ' + winpath(prefix, dest / name))
        for path in desktops:
            print('  Launcher routed through dllmgr: ' + str(path.absolute()))
        print('✓ FastStone fixes installed privately for ' + target)
        print_versions(state)
        install_trampoline(prefix, exe, package, base)
    print('  Launch: dllmgr run faststone')
    print('  Shared prefix DLLs and system Wine were not changed.')


def trampoline_registry(prefix, base):
    return prefill_proxy.Registry(prefix, str(base / 'bin/wine'))


def trampoline_line(prefix, exe):
    """Launcher line the proxy runs instead of a stock-Wine start."""
    launcher = (HERE.parent / 'dllmgr').resolve(strict=True)
    if '"' in str(prefix) + str(exe):
        raise prefill_proxy.Error('paths with double quotes are not supported')
    return f'"{winpath(prefix, launcher)}" run faststone --prefix "{prefix}" --exe "{exe}" --'


def install_trampoline(prefix, exe, package, base):
    """Best effort: without it only `dllmgr run` and the routed launchers get the fix."""
    try:
        with zipfile.ZipFile(package) as archive:
            if TRAMPOLINE_MEMBER not in archive.namelist():
                print('  Note: this runtime package has no launch trampoline; other launchers stay unfixed.')
                return
            data = archive.read(TRAMPOLINE_MEMBER)
    except zipfile.BadZipFile:
        return
    try:
        with tempfile.TemporaryDirectory(prefix='dllmgr-trampoline-') as directory:
            dll = Path(directory) / 'msimg32.dll'
            dll.write_bytes(data)
            reg = trampoline_registry(prefix, base)
            line = trampoline_line(prefix, exe)
            try:
                result = prefill_proxy.apply(prefix, exe, 'msimg32', dll, reg, line)
            except prefill_proxy.Error:
                if not prefill_proxy.state_path(prefix, exe).exists():
                    raise
                prefill_proxy.undo(prefix, exe, reg)  # older build or moved dllmgr
                result = prefill_proxy.apply(prefix, exe, 'msimg32', dll, reg, line)
        print('  Launch trampoline ' + result + ': any start of this FSViewer.exe gets the fixes.')
        print('    files: ' + str(exe.parent / 'msimg32.dll') + ' (sha256 ' + hashlib.sha256(data).hexdigest()[:12] +
              '), msimg32.dllmgr; load order: ' + prefill_proxy.key_for(exe) + ' msimg32=native,builtin')
    except Exception as error:  # optional part: never fail the installed fix
        print('  Warning: launch trampoline not installed (' + str(error) + '); use dllmgr run faststone.')


def uninstall_trampoline(prefix, exe, base):
    if not prefill_proxy.state_path(prefix, exe).exists():
        return
    try:
        prefill_proxy.undo(prefix, exe, trampoline_registry(prefix, base))
    except (prefill_proxy.Error, OSError, subprocess.SubprocessError) as error:
        print('  Warning: launch trampoline left in place (' + str(error) + ')')


def trampoline_status(prefix, exe, base):
    if not prefill_proxy.state_path(prefix, exe).exists():
        return 'absent'
    try:
        prefill_proxy.check(prefix, exe, trampoline_registry(prefix, base))
        return 'ok'
    except (prefill_proxy.Error, OSError, subprocess.SubprocessError) as error:
        return 'broken (' + str(error) + ')'


def recover(prefix, path):
    state = json.loads(path.read_text())
    if state.get('phase') != 'pending':
        return
    if (state.get('schema') != 1 or state.get('prefix') != str(prefix)
            or state.get('id') != path.stem or app_id(state.get('target', '')) != path.stem):
        raise Error('Invalid pending transaction; no files changed')
    transaction = state['transaction']
    changes = transaction['desktops']
    for entry in changes:
        desktop = Path(entry['path'])
        current = desktop.read_bytes() if desktop.exists() else None
        before = bytes.fromhex(entry['before_hex']) if entry['before_hex'] is not None else None
        if current != before and ((current is None and entry['after_sha256'] is not None) or (current is not None and hashlib.sha256(current).hexdigest() != entry['after_sha256'])):
            raise Error('Pending desktop entry changed outside dllmgr: ' + str(desktop))
    for entry in changes:
        desktop = Path(entry['path'])
        if entry['before_hex'] is None:
            desktop.unlink(missing_ok=True)
        else:
            atomic(desktop, bytes.fromhex(entry['before_hex']))
    previous = transaction['previous']
    if previous is None:
        path.unlink()
    else:
        save(path, previous)


def uninstall(args, prefix):
    path, state = read_state(prefix, args.exe)
    if args.fix != state['fix']:
        raise Error('A different recipe is installed: ' + state['fix'])
    directory = checked_files(prefix, state)
    for entry in state['desktops']:
        desktop = Path(entry['path'])
        if not desktop.is_file() or digest(desktop) != entry['installed_sha256']:
            raise Error('Desktop entry changed; refusing to overwrite: ' + str(desktop))
    changes = []
    for entry in state['desktops']:
        desktop = Path(entry['path'])
        before = bytes.fromhex(entry['before_hex']) if entry.get('before_hex') is not None else (entry['before'].encode() if entry.get('before') is not None else None)
        changes.append(dict(path=str(desktop), before_hex=desktop.read_bytes().hex(),
                            after_sha256=hashlib.sha256(before).hexdigest() if before is not None else None))
    uninstall_trampoline(prefix, Path(state['exe']), Path(state['base']))
    pending = dict(state, phase='pending', transaction=dict(previous=state, desktops=changes))
    save(path, pending)
    try:
        for entry in state['desktops']:
            desktop = Path(entry['path'])
            before = bytes.fromhex(entry['before_hex']) if entry.get('before_hex') is not None else (entry['before'].encode() if entry.get('before') is not None else None)
            if before is None:
                desktop.unlink()
            else:
                atomic(desktop, before)
        path.unlink()  # Commit removal before deleting now-unused immutable files.
    except BaseException:
        recover(prefix, path)
        raise
    for name in state['files']:
        (directory / name).unlink()
    directory.rmdir()
    print('✓ Private FastStone recipe removed; previous desktop entries restored.')


def launch(args, prefix):
    _, state = read_state(prefix, args.exe)
    exe = Path(state['exe'])
    if digest(exe) != state['exe_sha256'] or winpath(prefix, exe) != state['target']:
        raise Error('FastStone executable or drive mapping changed; reinstall its profile')
    directory = checked_files(prefix, state)
    runtime = Path(state['runtime'])
    verify(runtime, state['package_sha256'], Path(state['base']))
    verify_prefix(prefix, Path(state['base']))
    env = dict(os.environ)
    for name in RULES:
        env.pop(name, None)
    if 'utf' not in locale.getencoding().lower().replace('-', ''):
        env['LC_ALL'] = 'C.UTF-8'
    env.update(WINEPREFIX=str(prefix), WINEARCH='wow64', DLLMGR_TARGET_EXE=state['target'],
               WINELOADER=str(runtime / 'bin/wine'), WINESERVER=str(runtime / 'bin/wineserver'))
    for name in state['files']:
        env['DLLMGR_' + ('COMCTL32' if name == 'comctl32.dll' else 'GDIPLUS')] = winpath(prefix, directory / name)
    # ExecArguments stays an argv list; image filenames never become shell code.
    app_args = [winpath(prefix, Path(arg)) if Path(arg).is_file() else arg for arg in args.app_args]
    os.chdir(exe.parent)
    os.execve(runtime / 'bin/wine', [str(runtime / 'bin/wine'), state['target'], *app_args], env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall', 'run', 'status'])
    parser.add_argument('--prefix', type=Path, default=Path(os.environ.get('WINEPREFIX', str(Path.home() / '.wine'))))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--json', action='store_true', help='machine-readable status')
    parser.add_argument('--fix', default='faststone', choices=sorted(catalog_fixes.known()))
    parser.add_argument('--runtime-package', type=Path, help='explicit offline package (trusted local file)')
    parser.add_argument('--base-wine', type=Path, default=Path('/opt/wine-stable'))
    parser.add_argument('--desktop-entry', type=Path, action='append', default=[], help='also route this existing FastStone launcher; reversible')
    own_args, app_args = sys.argv[1:], []
    if '--' in own_args:
        cut = own_args.index('--')
        own_args, app_args = own_args[:cut], own_args[cut + 1:]
    args = parser.parse_args(own_args)
    args.app_args = app_args
    if app_args and args.command != 'run':
        parser.error('application arguments require run')
    prefix = args.prefix.resolve(strict=True)
    if not (prefix / 'system.reg').is_file():
        raise Error('Not an existing Wine prefix')
    with locked(prefix):
        for path in (prefix / STATE).glob('faststone-*.json'):
            if path.is_symlink():
                raise Error('Refusing a symlink ownership journal')
            recover(prefix, path)
        if args.command == 'install':
            install(args, prefix)
        elif args.command == 'uninstall':
            uninstall(args, prefix)
        elif args.command == 'status':
            _, state = read_state(prefix, args.exe)
            checked_files(prefix, state)
            verify(Path(state['runtime']), state['package_sha256'], Path(state['base']))
            trampoline = trampoline_status(prefix, Path(state['exe']), Path(state['base']))
            if args.json:
                print(json.dumps(dict(state, trampoline=trampoline), indent=2, ensure_ascii=False))
            else:
                print('✓ FastStone · ' + state['fix'] + ' · private DLLs verified')
                print('  ' + state['target'])
                print_versions(state)
                print('  Launch trampoline: ' + trampoline)
                print('  Launch: dllmgr run faststone')
        else:
            launch(args, prefix)


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('dllmgr: ' + str(error), file=sys.stderr)
        sys.exit(1)
