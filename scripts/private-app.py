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
import time
import urllib.request
import zipfile

import catalog_fixes
from ui import Progress
from private_runtime import Error, assemble, digest, overlay_for, package_manifest, valid_sha, verify

EXE_SHA = '05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621'
# Application profiles (PS-3, docs/plans/photoshop-cs2.md). FastStone keeps its
# original state format (no 'app' key); other profiles record theirs.
PROFILES = {
    'faststone': dict(
        title='FastStone', exe='fsviewer.exe', sha=None,  # None: EXE_SHA (read at call time)
        proxy='msimg32', modules=True,
        unsupported='Only the verified FastStone 8.5 x86 executable is supported',
        desktop_name='FastStone Image Viewer (dllmgr)', wmclass='fsviewer.exe',
        mime='image/jpeg;image/png;image/webp;image/avif;'),
    # #36 splash (version.dll prefill proxy), #43 focus, #44 cursors, #45 menus
    # (private runtime). No private DLLs.
    'photoshop-cs2': dict(
        title='Photoshop CS2', exe='photoshop.exe',
        sha=('98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30',), proxy='version', modules=False,
        unsupported='Only the verified Photoshop CS2 9.0 (trial) executable is supported',
        desktop_name='Adobe Photoshop CS2 (dllmgr)', wmclass='photoshop.exe',
        mime='image/vnd.adobe.photoshop;image/jpeg;image/png;image/tiff;image/bmp;'),
}
STATE = Path('.dllmgr/apps')
HERE = Path(__file__).resolve().parent
RULES = ('DLLMGR_TARGET_EXE', 'DLLMGR_COMCTL32', 'DLLMGR_GDIPLUS')

# User settings per application (#52), kept in the prefix and applied by
# `dllmgr run` as environment variables the private runtime reads.
SETTINGS = {
    'text': ('system', 'bitmap', 'gray', 'light', 'cleartype'),  # DLLMGR52_TEXT
    'contrast': None,  # DLLMGR52_GAMMA, 1.0 .. 4.0, smoothed text only
    'scaling': ('exact', 'smooth'),  # DLLMGR46_SMOOTH
}
SETTING_DEFAULTS = {
    'photoshop-cs2': {'text': 'gray', 'contrast': '2.2', 'scaling': 'exact'},
    'faststone': {'text': 'system', 'contrast': '1.6', 'scaling': 'exact'},
}
SETTINGS_FILE = '.dllmgr/settings.json'


def read_settings(prefix, app):
    values = dict(SETTING_DEFAULTS.get(app, {'text': 'system', 'contrast': '1.6', 'scaling': 'exact'}))
    try:
        stored = json.loads((prefix / SETTINGS_FILE).read_text()).get(app, {})
    except (OSError, ValueError, AttributeError):
        stored = {}
    values.update({k: str(v) for k, v in stored.items() if k in SETTINGS})
    return values


def check_setting(key, value):
    if key not in SETTINGS:
        raise Error('Unknown setting ' + key + ' (known: ' + ', '.join(SETTINGS) + ')')
    if SETTINGS[key] is None:
        try:
            ok = 1.0 <= float(value) <= 4.0
        except ValueError:
            ok = False
        if not ok:
            raise Error(key + ' must be a number from 1.0 to 4.0')
    elif value not in SETTINGS[key]:
        raise Error(key + ' must be one of: ' + ', '.join(SETTINGS[key]))


def write_settings(prefix, app, pairs):
    path = prefix / SETTINGS_FILE
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    current = data.setdefault(app, {})
    for pair in pairs:
        key, sep, value = pair.partition('=')
        if not sep:
            raise Error('Expected key=value, got ' + pair)
        check_setting(key, value)
        current[key] = value
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def settings_env(values):
    env = {}
    if values['text'] != 'system':
        env['DLLMGR52_TEXT'] = values['text']
        env['DLLMGR52_GAMMA'] = values['contrast']
    if values['scaling'] == 'smooth':
        env['DLLMGR46_SMOOTH'] = '1'
    return env


def settings_line(values):
    return ' '.join(k + '=' + values[k] for k in SETTINGS)
# #27 trampoline: proxy shipped in the runtime package (checksummed by its
# manifest); next to FSViewer.exe it relaunches stock-Wine starts through
# `dllmgr run faststone` (patches/dllmgr-27/README.md).
TRAMPOLINE_MEMBER = 'dllmgr-27/msimg32.dll'


def trampoline_member(app):
    return 'dllmgr-27/' + PROFILES[app]['proxy'] + '.dll'
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


LAUNCH_LOG = '.dllmgr/launch.log'


def launch_log(prefix, text):
    """One line per `dllmgr run` step, last 20 kept (#51: a run started by the
    launch trampoline has no visible terminal, so `status` shows these)."""
    path = prefix / LAUNCH_LOG
    try:
        lines = path.read_text(errors='replace').splitlines()[-19:] if path.is_file() else []
        path.parent.mkdir(exist_ok=True)
        stamp = time.strftime('%Y-%m-%d %H:%M:%S')
        path.write_text('\n'.join(lines + [stamp + ' pid ' + str(os.getpid()) + ' ' + text]) + '\n')
    except OSError:
        pass  # diagnostics only


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


def select(prefix, requested, app='faststone'):
    profile = PROFILES[app]
    if platform.machine() != 'x86_64' or '#arch=win64' not in (prefix / 'system.reg').read_text(errors='replace'):
        raise Error('This verified profile requires x86-64 Linux and a win64 prefix')
    if requested:
        exe = requested.resolve(strict=True)
    else:
        copies = sorted({p.resolve() for p in (prefix / 'drive_c').rglob('*')
                         if p.name.casefold() == profile['exe'] and p.is_file()})
        if len(copies) != 1:
            raise Error('Pass --exe to select exactly one ' + profile['title'] + ' installation')
        exe = copies[0]
    if exe.name.casefold() != profile['exe'] or digest(exe) not in (profile['sha'] or (EXE_SHA,)):
        raise Error(profile['unsupported'])
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


def app_id(target, app='faststone'):
    return app + '-' + hashlib.sha256(target.casefold().encode()).hexdigest()[:20]


def state_app(state):
    return state.get('app', 'faststone')


def state_paths(prefix, app):
    return [p for p in sorted((prefix / STATE).glob(app + '-*.json')) if re.fullmatch(re.escape(app) + '-[0-9a-f]{20}', p.stem)]


def read_state(prefix, exe=None, app='faststone'):
    paths = state_paths(prefix, app)
    if exe:
        paths = [prefix / STATE / (app_id(winpath(prefix, exe), app) + '.json')]
    if len(paths) != 1 or not paths[0].is_file():
        raise Error('Select one installed private ' + PROFILES[app]['title'] + ' profile with --exe')
    path = paths[0]
    if path.is_symlink():
        raise Error('Refusing a symlink ownership journal')
    state = json.loads(path.read_text())
    if (state.get('schema') != 1 or state.get('prefix') != str(prefix)
            or state_app(state) != app or state.get('id') != path.stem
            or app_id(state.get('target', ''), app) != path.stem
            or state.get('phase') != 'installed' or not valid_sha(state.get('exe_sha256'))):
        raise Error('Invalid private application journal; no files changed')
    return path, state


def checked_files(prefix, state):
    generation = state.get('generation', '')
    if not re.fullmatch('[0-9a-f]{64}', generation):
        raise Error('Invalid private generation')
    if not PROFILES.get(state_app(state), PROFILES['faststone'])['modules']:
        if state.get('files') != {}:
            raise Error('Invalid private module journal')
        return None  # runtime + proxy only, no private DLL directory
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
    revision = HERE.parent / '.dllmgr-revision'  # written by install.sh
    if revision.is_file():
        return revision.read_text().strip()[:7] + ' (installed)'
    try:
        return subprocess.check_output(['git', '-C', str(HERE.parent), 'log', '-1', '--format=%h %cs'],
                                       text=True, stderr=subprocess.DEVNULL).strip() or 'unknown'
    except (OSError, subprocess.SubprocessError):
        return 'unknown (' + str(HERE.parent) + ' is not a readable git checkout)'


def running_on(exe_name, proc=Path('/proc')):
    """(pid, 'private runtime' | 'system Wine' | '?') for running copies of exe_name (diagnostics, #44/#45)."""
    found = []
    for entry in proc.iterdir() if proc.is_dir() else ():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
            if exe_name.casefold() not in cmdline.casefold():
                continue
            maps = (entry / 'maps').read_text(errors='replace')
        except OSError:
            continue
        lines = [line for line in maps.splitlines() if line.endswith('/winex11.so')]
        if not lines:
            continue  # not a Wine process with a display (e.g. the launcher)
        kind = 'private runtime' if '/dllmgr/runtimes/' in lines[0] else 'system Wine'
        found.append((int(entry.name), kind))
    return found


def print_versions(state):
    print('  Versions: dllmgr ' + dllmgr_version() + ' · runtime ' +
          state.get('runtime_release', 'unknown (installed by an older dllmgr)') +
          ' (sha256 ' + state.get('package_sha256', '?')[:12] + ') · modules ' + str(state.get('release', '?') or 'none (runtime and proxy only)'))


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


def desktop_content(prefix, exe, app='faststone'):
    profile = PROFILES[app]
    launcher = Path.home() / '.local/bin/dllmgr'
    command = ' '.join(quote_desktop(x) for x in (launcher, 'run', app, '--prefix', prefix, '--exe', exe)) + ' -- %F'
    return ('[Desktop Entry]\nType=Application\nName=' + profile['desktop_name'] + '\n'
            'Comment=' + profile['title'] + ' with application-private Wine fixes\nExec=' + command + '\n'
            'Terminal=false\nStartupWMClass=' + profile['wmclass'] + '\nMimeType=' + profile['mime'] + '\n').encode()


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


def app_of(args):
    return getattr(args, 'app', 'faststone')  # older callers and tests


def install(args, prefix):
    app = app_of(args)
    profile = PROFILES[app]
    exe = select(prefix, args.exe, app)
    target = winpath(prefix, exe)
    ident = app_id(target, app)
    state_path = prefix / STATE / (ident + '.json')
    if state_path.parent.resolve() != state_path.parent.absolute():
        raise Error('Ownership directory must not contain symlinks')
    if profile['modules']:
        legacy_guard(prefix)
        for name in ('gdiplus.dll', 'comctl32.dll'):
            if (exe.parent / name).exists():
                raise Error('App-local ' + name + ' exists; archive/restore it with its original tool first')
    old = None
    if state_path.exists():
        _, old = read_state(prefix, exe, app)
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
        release, payloads = modules(args.fix, temp) if profile['modules'] else (None, {})
        hashes = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}
        generation = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
        dest = prefix / 'drive_c/dllmgr/apps' / ident / generation
        if not payloads:
            pass  # runtime + proxy only
        elif dest.exists():
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
        template = desktop_content(prefix, exe, app)
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
                     target=target, exe_sha256=digest(exe), fix=args.fix, release=release,
                     generation=generation, files=hashes, runtime=str(runtime), base=str(base),
                     package_sha256=digest(package), desktops=owned,
                     runtime_release=runtime_release(args.runtime_package))
        if app != 'faststone':
            state['app'] = app
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
        print('✓ ' + profile['title'] + ' fixes installed privately for ' + target)
        print_versions(state)
        install_trampoline(prefix, exe, package, base, app)
    print('  Launch: dllmgr run ' + app)
    print('  Shared prefix DLLs and system Wine were not changed.')


def stable_launcher():
    """The dllmgr command that survives upgrades: install.sh's symlink
    (~/.local/bin/dllmgr -> ~/.local/lib/dllmgr/<sha>/dllmgr) when this copy is
    an installed version, otherwise this checkout's own script."""
    own = (HERE.parent / 'dllmgr').resolve(strict=True)
    if (HERE.parent / '.dllmgr-revision').is_file():
        link = Path.home() / '.local/bin/dllmgr'
        if link.is_symlink() and link.resolve().parent.parent == HERE.parent.parent:
            return link
    return own


def trampoline_registry(prefix, base):
    return prefill_proxy.Registry(prefix, str(base / 'bin/wine'))


def trampoline_line(prefix, exe, app='faststone'):
    """Launcher line the proxy runs instead of a stock-Wine start."""
    launcher = stable_launcher()
    if '"' in str(prefix) + str(exe):
        raise prefill_proxy.Error('paths with double quotes are not supported')
    # Keep the launcher's own name (it may be the install.sh symlink that
    # follows upgrades); only its directory is resolved for the drive mapping.
    launcher_win = winpath(prefix, launcher.parent) + '\\' + launcher.name
    return f'"{launcher_win}" run {app} --prefix "{prefix}" --exe "{exe}" --'


def install_trampoline(prefix, exe, package, base, app='faststone'):
    """Best effort: without it only `dllmgr run` and the routed launchers get the fix."""
    proxy = PROFILES[app]['proxy']
    member = trampoline_member(app)
    try:
        with zipfile.ZipFile(package) as archive:
            if member not in archive.namelist():
                print('  Note: this runtime package has no ' + proxy + '.dll launch trampoline; other launchers stay unfixed.')
                return
            data = archive.read(member)
    except zipfile.BadZipFile:
        return
    try:
        with tempfile.TemporaryDirectory(prefix='dllmgr-trampoline-') as directory:
            dll = Path(directory) / (proxy + '.dll')
            dll.write_bytes(data)
            reg = trampoline_registry(prefix, base)
            line = trampoline_line(prefix, exe, app)
            try:
                result = prefill_proxy.apply(prefix, exe, proxy, dll, reg, line)
            except prefill_proxy.Error:
                if not prefill_proxy.state_path(prefix, exe).exists():
                    raise
                prefill_proxy.undo(prefix, exe, reg)  # older build, manual install or moved dllmgr
                result = prefill_proxy.apply(prefix, exe, proxy, dll, reg, line)
        print('  Launch trampoline ' + result + ': any start of this ' + exe.name + ' gets the fixes.')
        print('    files: ' + str(exe.parent / (proxy + '.dll')) + ' (sha256 ' + hashlib.sha256(data).hexdigest()[:12] +
              '), ' + proxy + '.dllmgr; load order: ' + prefill_proxy.key_for(exe) + ' ' + proxy + '=native,builtin')
    except Exception as error:  # optional part: never fail the installed fix
        print('  Warning: launch trampoline not installed (' + str(error) + '); use dllmgr run ' + app + '.')


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
            or state.get('id') != path.stem or app_id(state.get('target', ''), state_app(state)) != path.stem):
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
    path, state = read_state(prefix, args.exe, app_of(args))
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
    if directory is not None:
        for name in state['files']:
            (directory / name).unlink()
        directory.rmdir()
    print('✓ Private ' + PROFILES[app_of(args)]['title'] + ' recipe removed; previous desktop entries restored.')


def watched_run():
    """True when started by the launch trampoline: Wine starts Unix programs
    with a double fork, so we are orphaned (parent pid 1)."""
    return os.getppid() == 1 or bool(os.environ.get('DLLMGR_RUN_WATCH'))


KEEP_ENV = ('HOME', 'USER', 'LOGNAME', 'PATH', 'SHELL', 'DISPLAY', 'XAUTHORITY', 'WAYLAND_DISPLAY',
            'XDG_RUNTIME_DIR', 'XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_SESSION_TYPE',
            'DBUS_SESSION_BUS_ADDRESS', 'LANG', 'LANGUAGE', 'TZ')


def clean_env(env):
    """The environment a login session would give, plus our own variables:
    drops whatever the stock Wine process passed down to its Unix child."""
    keep = {k: v for k, v in env.items()
            if k in KEEP_ENV or k.startswith(('LC_', 'DLLMGR', 'WINEPREFIX', 'WINEARCH', 'WINELOADER', 'WINESERVER'))}
    return keep


def watch(prefix, app, argv, env, quick=3.0):
    """Started by the launch trampoline (Wine's double fork leaves us orphaned):
    nobody sees our output, so keep the private Wine's stderr in the prefix and
    record how it ended (#51). Runs outside the prefix lock, so `status` works
    meanwhile. When the private Wine dies within `quick` seconds, retry with
    half of the suspects removed (first the inherited environment, then with
    loader traces) and log which attempt worked: the stock process waits up
    to 15 s, so the user still gets the private runtime."""
    clean = clean_env(env)
    attempts = [('inherited environment', env), ('clean environment', clean),
                ('clean environment, traced', dict(clean, WINEDEBUG='+process,+loaddll'))]
    log = prefix / '.dllmgr/trampoline-run.log'
    extra = sorted(set(env) - set(clean))
    for number, (what, attempt_env) in enumerate(attempts):
        started = time.monotonic()
        try:
            with open(log, 'w' if number == 0 else 'a') as out:
                out.write('== attempt %d: %s\n' % (number + 1, what))
        except OSError:
            pass
        pid = os.fork()
        if pid == 0:
            try:
                fd = os.open(log, os.O_WRONLY | os.O_APPEND)
                os.dup2(fd, 2)
                os.close(fd)
            except OSError:
                pass
            try:
                os.execve(argv[0], argv, attempt_env)
            finally:
                os._exit(127)
        _, status = os.waitpid(pid, 0)
        took = time.monotonic() - started
        how = ('exit code ' + str(os.waitstatus_to_exitcode(status))) if os.WIFEXITED(status) else 'signal ' + str(os.WTERMSIG(status))
        launch_log(prefix, 'run %s: private runtime (%s) ended (%s) after %.1f s; stderr: .dllmgr/trampoline-run.log' % (app, what, how, took))
        if number == 0 and extra:
            launch_log(prefix, 'run %s: inherited variables not in the clean environment: %s' % (app, ' '.join(extra)[:600]))
        if took >= quick or status == 0:
            return


def launch(args, prefix):
    _, state = read_state(prefix, args.exe, app_of(args))
    exe = Path(state['exe'])
    if digest(exe) != state['exe_sha256'] or winpath(prefix, exe) != state['target']:
        raise Error(PROFILES[app_of(args)]['title'] + ' executable or drive mapping changed; reinstall its profile')
    directory = checked_files(prefix, state)
    runtime = Path(state['runtime'])
    verify(runtime, state['package_sha256'], Path(state['base']))
    verify_prefix(prefix, Path(state['base']))
    env = dict(os.environ)
    for name in RULES + ('DLLMGR52_TEXT', 'DLLMGR52_GAMMA', 'DLLMGR46_SMOOTH'):
        env.pop(name, None)
    env.update(settings_env(read_settings(prefix, app_of(args))))
    if 'utf' not in locale.getencoding().lower().replace('-', ''):
        env['LC_ALL'] = 'C.UTF-8'
    env.update(WINEPREFIX=str(prefix), WINEARCH='wow64', DLLMGR_TARGET_EXE=state['target'],
               WINELOADER=str(runtime / 'bin/wine'), WINESERVER=str(runtime / 'bin/wineserver'))
    for name in state['files'] if directory is not None else ():
        env['DLLMGR_' + ('COMCTL32' if name == 'comctl32.dll' else 'GDIPLUS')] = winpath(prefix, directory / name)
    # ExecArguments stays an argv list; image filenames never become shell code.
    app_args = [winpath(prefix, Path(arg)) if Path(arg).is_file() else arg for arg in args.app_args]
    os.chdir(exe.parent)
    argv = [str(runtime / 'bin/wine'), state['target'], *app_args]
    launch_log(prefix, 'run ' + app_of(args) + ': starting the private runtime')
    if not watched_run():
        os.execve(runtime / 'bin/wine', argv, env)
        return  # only reached when execve is mocked in tests
    return argv, env  # watched: started outside the prefix lock by watch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall', 'run', 'status', 'set'])
    parser.add_argument('values', nargs='*', help='set: key=value pairs (text, contrast, scaling)')
    parser.add_argument('--prefix', type=Path, default=Path(os.environ.get('WINEPREFIX', str(Path.home() / '.wine'))))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--json', action='store_true', help='machine-readable status')
    parser.add_argument('--app', default='faststone', choices=sorted(PROFILES))
    parser.add_argument('--fix', choices=sorted(catalog_fixes.known()), help='FastStone recipe (default faststone)')
    parser.add_argument('--runtime-package', type=Path, help='explicit offline package (trusted local file)')
    parser.add_argument('--base-wine', type=Path, default=Path('/opt/wine-stable'))
    parser.add_argument('--desktop-entry', type=Path, action='append', default=[], help='also route this existing FastStone launcher; reversible')
    own_args, app_args = sys.argv[1:], []
    if '--' in own_args:
        cut = own_args.index('--')
        own_args, app_args = own_args[:cut], own_args[cut + 1:]
    args = parser.parse_args(own_args)
    args.app_args = app_args
    if args.app == 'faststone':
        args.fix = args.fix or 'faststone'
    elif args.fix:
        parser.error('--fix applies to faststone only')
    else:
        args.fix = args.app
    if args.values and args.command != 'set':
        parser.error('key=value pairs require set')
    if app_args and args.command != 'run':
        parser.error('application arguments require run')
    prefix = args.prefix.resolve(strict=True)
    if not (prefix / 'system.reg').is_file():
        raise Error('Not an existing Wine prefix')
    if args.command == 'run':
        launch_log(prefix, 'run ' + args.app + ': started (parent pid ' + str(os.getppid()) + ')')
    watched = None
    with locked(prefix):
        for path in [p for app in PROFILES for p in state_paths(prefix, app)]:
            if path.is_symlink():
                raise Error('Refusing a symlink ownership journal')
            recover(prefix, path)
        if args.command == 'install':
            install(args, prefix)
        elif args.command == 'uninstall':
            uninstall(args, prefix)
        elif args.command == 'set':
            if not args.values:
                print(settings_line(read_settings(prefix, args.app)))
            else:
                write_settings(prefix, args.app, args.values)
                print('Settings for ' + args.app + ': ' + settings_line(read_settings(prefix, args.app)) +
                      ' (applied at the next start)')
        elif args.command == 'status':
            _, state = read_state(prefix, args.exe, args.app)
            checked_files(prefix, state)
            verify(Path(state['runtime']), state['package_sha256'], Path(state['base']))
            trampoline = trampoline_status(prefix, Path(state['exe']), Path(state['base']))
            if args.json:
                print(json.dumps(dict(state, trampoline=trampoline), indent=2, ensure_ascii=False))
            else:
                print('✓ ' + PROFILES[args.app]['title'] + ' · ' + state['fix'] + ' · private ' +
                      ('DLLs' if state['files'] else 'runtime') + ' verified')
                print('  ' + state['target'])
                print_versions(state)
                print('  Launch trampoline: ' + trampoline)
                print('  Settings: ' + settings_line(read_settings(prefix, args.app)) +
                      ' (change: dllmgr set ' + args.app + ' text=' + '|'.join(SETTINGS['text']) +
                      ' contrast=1.0..4.0 scaling=exact|smooth)')
                print('  Launch: dllmgr run ' + args.app)
                for pid, kind in running_on(Path(state['exe']).name):
                    print('  Running: pid ' + str(pid) + ' on the ' + kind)
                log = prefix / LAUNCH_LOG
                last = [l for l in log.read_text(errors='replace').splitlines() if ' run ' + args.app + ':' in l][-2:] if log.is_file() else []
                for line in last:
                    print('  Last launches: ' + line if line is last[0] else '                 ' + line)
        else:
            try:
                watched = launch(args, prefix)
            except BaseException as error:
                launch_log(prefix, 'run ' + args.app + ': failed: ' + (str(error) or type(error).__name__))
                raise
    if args.command == 'run' and watched:
        watch(prefix, args.app, *watched)


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('dllmgr: ' + str(error), file=sys.stderr)
        sys.exit(1)
