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
        # #73: the formats FastStone 8.5 opens itself (its folder ships jxl/webp/avif codecs)
        mime='image/jpeg;image/png;image/gif;image/bmp;image/tiff;image/webp;image/avif;image/jxl;'
             'image/x-icon;image/vnd.microsoft.icon;image/x-tga;image/x-pcx;image/jp2;'
             'image/vnd.adobe.photoshop;image/x-adobe-dng;image/x-canon-cr2;image/x-canon-cr3;'
             'image/x-nikon-nef;image/x-sony-arw;image/x-olympus-orf;image/x-panasonic-rw2;image/x-fuji-raf;'),
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
    'text': ('system', 'bitmap', 'gray', 'light', 'cleartype', 'agg', 'agg-rgb'),  # DLLMGR52_TEXT; agg*: #69
    'contrast': None,  # DLLMGR52_GAMMA, 1.0 .. 4.0, smoothed text only
    'scaling': ('exact', 'smooth'),  # DLLMGR46_SMOOTH
    'alt-click': ('app', 'desktop'),  # #48: who gets Alt+click, see free_alt_click
    'tahoma': ('wine', 'xo', 'xo-bold', 'dejavu', 'dejavu-bold'),  # #66: DLLMGR66_TAHOMA[_BOLD]
    # #47/#65 finding: Wine's TWAIN source (sane.ds) asks libsane for devices when an
    # application lists TWAIN sources; Photoshop does that at every start and libsane
    # probes all its backends (~4.5 s of a 19 s start on the stand). off: no SANE
    # backends for this application (SANE_CONFIG_DIR points nowhere), no TWAIN scanning.
    # Default on everywhere: features are never switched off without the owner's
    # explicit permission (owner, 2026-11-10); the real fix is a lazy sane.ds.
    'scanner': ('off', 'on'),
    # #77: the raster "System" font (vgasys.fon) served by a smoothed TrueType
    # family inside the application (patches/dllmgr-77.patch, DLLMGR77_SYSTEM).
    # Beyond Windows, which also draws it as a raster font; the owner asked for it
    # for Photoshop CS2's activation dialog headings.
    'system': ('raster', 'tahoma'),
    # #71/#76: every start, from any launcher (menu, `dllmgr run`, plain
    # `wine APP.exe` through the trampoline), keeps a log in .dllmgr/runs
    # with loader lines (+loaddll) unless WINEDEBUG is set; `dllmgr logs APP`
    # zips them. off: no +loaddll (the run logs themselves stay).
    'logs': ('on', 'off'),
}
SYSTEM_FAMILIES = {'tahoma': 'Tahoma'}
# #66: Tahoma served by another family inside the application (the runtime's
# win32u, patches/dllmgr-66.patch); '-bold' only replaces bold Tahoma. XO Tahion
# ships with dllmgr (scripts/fonts/xo-tahion) and is copied into the prefix.
TAHOMA_FAMILIES = {'xo': 'XO Tahion', 'dejavu': 'DejaVu Sans Condensed'}
TAHOMA_FONTS = {'xo': HERE / 'fonts/xo-tahion'}
SETTING_DEFAULTS = {
    'photoshop-cs2': {'text': 'gray', 'contrast': '2.2', 'scaling': 'exact', 'alt-click': 'app', 'tahoma': 'wine', 'system': 'tahoma'},
    'faststone': {'text': 'system', 'contrast': '1.6', 'scaling': 'exact', 'alt-click': 'desktop', 'tahoma': 'wine'},
}
SETTINGS_FILE = '.dllmgr/settings.json'


def read_settings(prefix, app):
    values = dict(SETTING_DEFAULTS.get(app, {'text': 'system', 'contrast': '1.6', 'scaling': 'exact', 'alt-click': 'desktop', 'tahoma': 'wine'}))
    values.setdefault('scanner', 'on')
    values.setdefault('system', 'raster')
    values.setdefault('logs', 'on')
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
    family = TAHOMA_FAMILIES.get(values['tahoma'].split('-')[0])
    if family:
        env['DLLMGR66_TAHOMA_BOLD' if values['tahoma'].endswith('-bold') else 'DLLMGR66_TAHOMA'] = family
    if SYSTEM_FAMILIES.get(values.get('system')):
        env['DLLMGR77_SYSTEM'] = SYSTEM_FAMILIES[values['system']]
    if values.get('scanner') == 'off':
        env['SANE_CONFIG_DIR'] = '/nonexistent/dllmgr-scanner-off'
    return env


def install_tahoma_fonts(prefix, values):
    """#66: the shipped substitute family into the prefix's Fonts (Wine loads it from there)."""
    source = TAHOMA_FONTS.get(values['tahoma'].split('-')[0])
    if not source:
        return
    fonts = prefix / 'drive_c/windows/Fonts'
    fonts.mkdir(parents=True, exist_ok=True)
    for font in sorted(source.glob('*.ttf')):
        target = fonts / font.name
        if not target.is_file() or target.read_bytes() != font.read_bytes():
            shutil.copyfile(font, target)


# #48: Cinnamon (Muffin) moves windows on Alt+drag (its default modifier), so
# Alt+click never reaches the application (Photoshop: Zoom out, Eyedropper,
# Clone source...). On Windows Alt+click belongs to the application. While the
# application runs, the window modifier is switched to Super and restored when
# the prefix's wineserver ends (a detached `wm-restore` waits for it). The mark
# file keeps the original value, so a lost restorer is redone at the next start.
WM_SCHEMA, WM_KEY, WM_MARK = 'org.cinnamon.desktop.wm.preferences', 'mouse-button-modifier', '.dllmgr/wm-modifier'


def gsettings(*args):
    try:
        done = subprocess.run(['gsettings', *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def free_alt_click(prefix, app, env):
    current = gsettings('get', WM_SCHEMA, WM_KEY)
    mark = prefix / WM_MARK
    if current == "'<Alt>'":
        if gsettings('set', WM_SCHEMA, WM_KEY, '<Super>') is None:
            return
        mark.write_text('<Alt>\n')
        launch_log(prefix, 'run %s: Alt+click goes to the application: window modifier Alt -> Super until it ends (dllmgr set %s alt-click=desktop keeps Alt)' % (app, app))
    elif not (current == "'<Super>'" and mark.is_file()):
        return
    subprocess.Popen([sys.executable, os.path.abspath(__file__), 'wm-restore', str(os.getpid()), '--prefix', str(prefix), '--app', app],
                     env=env, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restore_alt_click(prefix, app, pid, poll=1.0):
    """Waits for the launching process (watcher or the exec'd Wine), then for
    the prefix's wineserver, then puts the window modifier back."""
    while Path('/proc/%d' % pid).exists() and not Path('/proc/%d/stat' % pid).read_text(errors='replace').split(') ')[-1].startswith('Z'):
        time.sleep(poll)
    server = os.environ.get('WINESERVER')
    if server:
        subprocess.run([server, '-w'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mark = prefix / WM_MARK
    if not mark.is_file():
        return
    original = mark.read_text().strip()
    if gsettings('get', WM_SCHEMA, WM_KEY) == "'<Super>'" and original in ('<Alt>',):
        gsettings('set', WM_SCHEMA, WM_KEY, original)
        if gsettings('get', WM_SCHEMA, WM_KEY) != "'" + original + "'":  # e.g. the session bus is gone (logout)
            launch_log(prefix, 'run %s: could not restore the window modifier %s; retried at the next start' % (app, original))
            return
        launch_log(prefix, 'run %s: window modifier restored to %s' % (app, original))
    mark.unlink(missing_ok=True)


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


def download_cache():
    """#75: verified downloads by sha256, so a second `dllmgr fix` does not fetch them again."""
    return Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'dllmgr/downloads'


def download(url, dest, checksum=None, label=None, keep=12):
    cached = download_cache() / checksum if checksum else None
    if cached and cached.is_file() and digest(cached) == checksum:
        shutil.copyfile(cached, dest)
        os.utime(cached)
        if label:
            print('  ' + label.replace('Downloading', 'Cached', 1) + ' (no download)')
        return
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
    if cached:
        try:
            cached.parent.mkdir(parents=True, exist_ok=True)
            tmp = cached.with_name(cached.name + '.tmp')
            shutil.copyfile(dest, tmp)
            tmp.replace(cached)
            for old in sorted(cached.parent.iterdir(), key=lambda f: f.stat().st_mtime)[:-keep]:
                old.unlink(missing_ok=True)
        except OSError:
            pass  # the cache is only a saving


def patched_modules(package):
    try:
        return ', '.join(sorted('/'.join(Path(dest).parts[-2:]) for dest in overlay_for(package_manifest(package)).values()))
    except (Error, KeyError, ValueError, zipfile.BadZipFile):
        return 'unknown (package without a readable manifest)'


def runtime_release(requested):
    """Human-readable runtime origin: release tag of the pin, or a local package."""
    if requested:
        return 'local package ' + str(requested)
    config = json.loads((HERE / 'private-runtime.json').read_text())
    if config.get('release'):  # published on the runtime-releases branch (raw URL)
        return config['release']
    url = config.get('url', '')
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


def dllmgr_revision():
    """Full commit of this dllmgr for the app journal (`dllmgr upgrade` compares
    it): install.sh's record, else a clean checkout's HEAD; None when unknown."""
    record = HERE.parent / '.dllmgr-revision'
    if record.is_file():
        value = record.read_text().strip()
        return value if re.fullmatch('[0-9a-f]{40}', value) else None
    try:
        git = ['git', '-C', str(HERE.parent)]
        if subprocess.check_output(git + ['status', '--porcelain', '--', 'dllmgr', 'catalog', 'patches', 'scripts'],
                                   text=True, stderr=subprocess.DEVNULL).strip():
            return None  # local edits: no commit describes this code
        value = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
        return value if re.fullmatch('[0-9a-f]{40}', value) else None
    except (OSError, subprocess.SubprocessError):
        return None


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
                     runtime_release=runtime_release(args.runtime_package),
                     dllmgr_revision=dllmgr_revision())
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
    if assoc_record(prefix, state_app(state)).is_file():  # #73: give the file types back first
        assoc(prefix, state_app(state), state, ['undo'])
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


def trampoline_summary(prefix, limit=12):
    """#51: what the last run started by the launch trampoline said: its
    attempts, Wine's err: and loader lines (the cause of a failed start) and
    its last lines, so a report needs only `dllmgr status`."""
    log = prefix / '.dllmgr/trampoline-run.log'
    try:
        lines = log.read_text(errors='replace').splitlines()
        when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log.stat().st_mtime))
    except OSError:
        return []
    # attempts, Wine's err: lines and anything that is not a fixme/warn/trace
    # ("wine: ..." loader messages), plus the tail of the log
    picked = [l for l in lines if l.startswith('== attempt') or ':err:' in l or
              not re.search(r'^[0-9a-f]{4}:(fixme|warn|trace):', l)]
    picked += [l for l in lines[-3:] if l not in picked]
    errors = [l for l in picked if ':err:' in l]
    if len(errors) > limit:  # keep attempt headers, the first errors of each kind
        seen, keep = set(), []
        for l in picked:
            kind = l.split(':err:', 1)[-1].split(' ', 1)[0] if ':err:' in l else l
            if ':err:' not in l or kind not in seen:
                keep.append(l)
                seen.add(kind)
        picked = keep
    return ['Last trampoline run (' + when + ', .dllmgr/trampoline-run.log):'] + ['  ' + l[:200] for l in picked[:limit * 2]]


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
        try:
            with open(log, 'rb') as tail_file:
                tail_file.seek(max(0, tail_file.seek(0, 2) - 16384))
                tail = tail_file.read().decode(errors='replace')
        except OSError:
            tail = ''
        how = run_verdict(os.waitstatus_to_exitcode(status), tail)  # #71
        launch_log(prefix, 'run %s: private runtime (%s) ended (%s) after %.1f s; stderr: .dllmgr/trampoline-run.log' % (app, what, how, took))
        if number == 0 and extra:
            launch_log(prefix, 'run %s: inherited variables not in the clean environment: %s' % (app, ' '.join(extra)[:600]))
        if took >= quick or status == 0:
            break
    try:  # #71/#76: keep it past the next start, beside the terminal runs
        runs = prefix / RUN_LOGS
        runs.mkdir(parents=True, exist_ok=True)
        rotate_runs(runs)
        shutil.copyfile(log, runs / ('trampoline-' + time.strftime('%Y%m%d-%H%M%S') + '.log'))
    except OSError:
        pass


def prefix_server(prefix, proc=Path('/proc')):
    """#78: the binary of the wineserver that already serves this prefix, or
    None. Wine starts a server only when none runs, so after a trampoline
    launch (stock wine started the exe) the private runtime gets the stock
    server, and a fix that lives only in wineserver does not apply."""
    try:
        st = os.stat(prefix)
    except OSError:
        return None
    sdir = '/tmp/.wine-%d/server-%x-%x' % (os.getuid(), st.st_dev, st.st_ino)
    for entry in proc.glob('[0-9]*'):
        try:
            if (entry / 'comm').read_text().strip() == 'wineserver' and os.readlink(entry / 'cwd') == sdir:
                return os.readlink(entry / 'exe')
        except OSError:
            continue
    return None


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
    for name in RULES + ('DLLMGR52_TEXT', 'DLLMGR52_GAMMA', 'DLLMGR46_SMOOTH', 'DLLMGR66_TAHOMA', 'DLLMGR66_TAHOMA_BOLD', 'DLLMGR77_SYSTEM'):
        env.pop(name, None)
    env.update(settings_env(read_settings(prefix, app_of(args))))
    install_tahoma_fonts(prefix, read_settings(prefix, app_of(args)))
    if 'utf' not in locale.getencoding().lower().replace('-', ''):
        env['LC_ALL'] = 'C.UTF-8'
    env.update(WINEPREFIX=str(prefix), WINEARCH='wow64', DLLMGR_TARGET_EXE=state['target'],
               WINELOADER=str(runtime / 'bin/wine'), WINESERVER=str(runtime / 'bin/wineserver'))
    for name in state['files'] if directory is not None else ():
        env['DLLMGR_' + ('COMCTL32' if name == 'comctl32.dll' else 'GDIPLUS')] = winpath(prefix, directory / name)
    if app_of(args) == 'faststone' and '"' not in str(HERE) and "'" not in str(HERE):
        # #73: FastStone's "Association Settings" button opens dllmgr's file-type dialog (msimg32 proxy)
        env['DLLMGR73_ASSOC'] = "'" + str(HERE.parent / 'dllmgr') + "' assoc faststone dialog"
    # ExecArguments stays an argv list; image filenames never become shell code.
    app_args = [winpath(prefix, Path(arg)) if Path(arg).is_file() else arg for arg in args.app_args]
    os.chdir(exe.parent)
    argv = [str(runtime / 'bin/wine'), state['target'], *app_args]
    if read_settings(prefix, app_of(args))['alt-click'] == 'app':
        free_alt_click(prefix, app_of(args), env)
    if read_settings(prefix, app_of(args))['logs'] == 'on' and not env.get('WINEDEBUG'):
        env['WINEDEBUG'] = RUN_WINEDEBUG  # #76: which module sat at a crash address
    server = prefix_server(prefix)
    launch_log(prefix, 'run ' + app_of(args) + ': starting the private runtime; wineserver: ' +
               ('already running ' + server + ('' if server == str(runtime / 'bin/wineserver') else ' (not the runtime\'s)')
                if server else 'none running, the runtime starts its own'))
    return argv, env  # started outside the prefix lock by watch() or supervise()


RUN_LOGS = '.dllmgr/runs'
RUN_KEEP = 20
RUN_WINEDEBUG = '+loaddll'


def rotate_runs(logs, keep=RUN_KEEP):
    """Room for one more run log: keep the newest keep - 1 (both kinds)."""
    old = sorted(logs.glob('*.log'), key=lambda p: p.name.split('-', 1)[-1])
    for path in old[:max(0, len(old) - (keep - 1))]:
        path.unlink(missing_ok=True)
CRASH_MARKS = ('Unhandled exception', 'unhandled exception', 'page fault', 'Backtrace:', 'starting debugger')


def run_verdict(code, log_tail):
    """#71: one line on how a run ended, from the exit status and the log."""
    how = ('exit code %d' % code) if code >= 0 else ('signal %d' % -code)
    if any(mark in log_tail for mark in CRASH_MARKS):
        inside = [l.split('is inside ', 1)[1].split(' (base', 1)[0] for l in log_tail.splitlines()
                  if l.startswith('dllmgr76:') and ' is inside ' in l]
        # #76: the proxy's crash report names the module a bad pointer pointed into
        return how + ', crashed: unhandled exception in the log' + ('; the address was inside ' + inside[-1] if inside else '')
    clicked = [l.split('clicked ', 1)[1].strip() for l in log_tail.splitlines() if l.startswith('dllmgr71:') and ' clicked ' in l]
    if clicked:  # the version.dll proxy's exit report (#71): the last button pressed
        return how + ', the application closed itself; last button: ' + clicked[-1]
    if code == 0 and ('CoSuspendClassObjects' in log_tail or 'dllmgr71: process exit' in log_tail):
        return how + ', the application closed itself (orderly exit)'
    return how


def supervise(prefix, app, argv, env, keep=RUN_KEEP):
    """#71: start the private Wine from a terminal and stay its parent: its
    stderr goes to the terminal and to .dllmgr/runs/run-TIME.log (the last
    `keep` runs are kept), and launch.log gets how and when it ended."""
    logs = prefix / RUN_LOGS
    logs.mkdir(parents=True, exist_ok=True)
    rotate_runs(logs, keep)
    name = 'run-' + time.strftime('%Y%m%d-%H%M%S') + '.log'
    started = time.monotonic()
    tail = b''
    with open(logs / name, 'wb') as out:
        proc = subprocess.Popen(argv, env=env, stderr=subprocess.PIPE)
        while True:
            try:
                chunk = proc.stderr.read1(65536)
            except KeyboardInterrupt:  # Ctrl+C reaches Wine too; keep logging until it ends
                continue
            if not chunk:
                break
            out.write(chunk)
            out.flush()
            tail = (tail + chunk)[-16384:]
            if b':trace:loaddll:' in chunk:  # the log's loader lines stay out of the terminal
                chunk = b''.join(l for l in chunk.splitlines(True) if b':trace:loaddll:' not in l)
            try:
                sys.stderr.buffer.write(chunk)
                sys.stderr.flush()
            except OSError:
                pass  # terminal gone: keep the log
        while True:
            try:
                code = proc.wait()
                break
            except KeyboardInterrupt:
                continue
    verdict = run_verdict(code, tail.decode(errors='replace'))
    launch_log(prefix, 'run %s: ended (%s) after %.0f s; log: %s/%s' % (app, verdict, time.monotonic() - started, RUN_LOGS, name))
    return code


def downloads_dir():
    try:
        found = subprocess.run(['xdg-user-dir', 'DOWNLOAD'], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        found = ''
    path = Path(found) if found and Path(found) != Path.home() else Path.home() / 'Downloads'
    return path if path.is_dir() else Path.home()


def logs_bundle(prefix, app, out_dir=None):
    """#71/#76: one zip for the owner to send: the run logs, launch.log,
    the last trampoline log, settings and installed versions. Read-only."""
    out = (out_dir or downloads_dir()) / ('dllmgr-logs-' + app + '-' + time.strftime('%Y%m%d-%H%M%S') + '.zip')
    names = sorted((prefix / RUN_LOGS).glob('*.log')) if (prefix / RUN_LOGS).is_dir() else []
    extra = [prefix / LAUNCH_LOG, prefix / '.dllmgr/trampoline-run.log', prefix / SETTINGS_FILE]
    try:
        _, state = read_state(prefix, None, app)
        versions = dict(state)
    except (Error, OSError, ValueError, KeyError) as error:
        versions = {'state': 'not readable: ' + str(error)}
    versions.update(dllmgr=dllmgr_version(), app=app, prefix=str(prefix), created=time.strftime('%Y-%m-%d %H:%M:%S %z'),
                    host=platform.platform())
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in names:
            bundle.write(path, 'runs/' + path.name)
        for path in extra:
            if path.is_file():
                bundle.write(path, path.name)
        bundle.writestr('versions.json', json.dumps(versions, indent=2, ensure_ascii=False) + '\n')
    return out, len(names)


# #73 file associations, the freedesktop way: the defaults live in
# $XDG_CONFIG_HOME/mimeapps.list ([Default Applications]), which Cinnamon,
# Nemo and xdg-open read. Previous defaults are recorded per application in
# the prefix so "assoc APP undo" and uninstall put them back.
ASSOC_SECTION = '[Default Applications]'


def mimeapps_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'mimeapps.list'


def mimeapps_defaults(text):
    result, section = {}, None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('['):
            section = stripped
        elif section == ASSOC_SECTION and '=' in stripped and not stripped.startswith('#'):
            key, value = stripped.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def mimeapps_update(text, changes):
    """Set (value str) or remove (value None) keys of [Default Applications]; other lines stay as they are."""
    lines, out, section, done = text.splitlines(), [], None, set()

    def flush():
        for key, value in changes.items():
            if key not in done and value is not None:
                out.append(key + '=' + value)
            done.add(key)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('['):
            if section == ASSOC_SECTION:
                flush()
            section = stripped
        elif section == ASSOC_SECTION and '=' in stripped and stripped.split('=', 1)[0].strip() in changes:
            key = stripped.split('=', 1)[0].strip()
            if key not in done and changes[key] is not None:
                out.append(key + '=' + changes[key])
            done.add(key)
            continue
        out.append(line)
    if section == ASSOC_SECTION:
        flush()
    if any(v is not None and k not in done for k, v in changes.items()):
        if out and out[-1].strip():
            out.append('')
        out.append(ASSOC_SECTION)
        flush()
    return '\n'.join(out) + '\n'


def assoc_record(prefix, app):
    return prefix / '.dllmgr' / ('assoc-' + app + '.json')


def assoc(prefix, app, state, values):
    ours = Path(state['desktops'][0]['path']).name
    types = [t for t in PROFILES[app]['mime'].split(';') if t]
    path, record_path = mimeapps_path(), assoc_record(prefix, app)
    text = path.read_text() if path.is_file() else ''
    current = mimeapps_defaults(text)
    record = json.loads(record_path.read_text()) if record_path.is_file() else {}
    if not values:
        for t in types:
            print(('* ' if current.get(t, '').split(';')[0] == ours else '  ') + t + ': ' + (current.get(t) or '(not set)'))
        print('Set: dllmgr assoc ' + app + ' all | TYPE...   Undo: dllmgr assoc ' + app + ' undo')
        return
    if values == ['dialog']:  # #73: checklist (zenity), from FastStone's "Association Settings"
        rows = []
        for t in types:
            rows += ['TRUE' if current.get(t, '').split(';')[0] == ours else 'FALSE', t]
        try:
            answer = subprocess.run(['zenity', '--list', '--checklist', '--title', 'File types for ' + PROFILES[app]['title'],
                                     '--text', 'Open these file types with ' + PROFILES[app]['title'] + ' by default:',
                                     '--column', 'Default', '--column', 'Type', '--separator', ' ',
                                     '--width', '480', '--height', '560', *rows], capture_output=True, text=True)
        except FileNotFoundError:
            raise Error('zenity is not installed; use: dllmgr assoc ' + app + ' all | TYPE... | undo')
        if answer.returncode != 0:
            return
        chosen = answer.stdout.split()
        set_types = [t for t in chosen if t in types and current.get(t, '').split(';')[0] != ours]
        drop = [t for t in types if t not in chosen and current.get(t, '').split(';')[0] == ours]
        changes = {}
        for t in set_types:
            record.setdefault(t, current.get(t, ''))
            changes[t] = ours + ';'
        for t in drop:
            changes[t] = record.pop(t, '') or None
    elif values == ['undo']:
        changes = {t: (old or None) for t, old in record.items() if current.get(t, '').split(';')[0] == ours}
        record = {}
    else:
        alias = {'psd': 'vnd.adobe.photoshop', 'jpg': 'jpeg', 'jpe': 'jpeg', 'tif': 'tiff', 'ico': 'x-icon', 'tga': 'x-tga', 'pcx': 'x-pcx', 'dng': 'x-adobe-dng', 'cr2': 'x-canon-cr2', 'cr3': 'x-canon-cr3', 'nef': 'x-nikon-nef', 'arw': 'x-sony-arw', 'orf': 'x-olympus-orf', 'rw2': 'x-panasonic-rw2', 'raf': 'x-fuji-raf'}
        wanted = types if values == ['all'] else [next((t for t in types if t == v or t.endswith('/' + alias.get(v.lower(), v.lower()))), None) for v in values]
        if None in wanted:
            raise Error('Unknown type; choose from ' + ' '.join(types))
        changes = {}
        for t in wanted:
            if current.get(t, '').split(';')[0] != ours:
                record.setdefault(t, current.get(t, ''))
                changes[t] = ours + ';'
    if changes:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.dllmgr-tmp')
        tmp.write_text(mimeapps_update(text, changes))
        tmp.replace(path)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    if record:
        record_path.write_text(json.dumps(record, indent=2))
    elif record_path.exists():
        record_path.unlink()
    print('Associations for ' + app + ': ' + (', '.join(sorted(changes)) + (' restored' if values == ['undo'] else ' -> ' + ours)
                                               if changes else 'nothing to change'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall', 'run', 'status', 'set', 'assoc', 'logs', 'wm-restore'])
    parser.add_argument('values', nargs='*', help='set: key=value pairs (text, contrast, scaling, alt-click, tahoma, system, scanner); assoc: all | TYPE... | undo')
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
    args = parser.parse_intermixed_args(own_args)
    args.app_args = app_args
    if args.app == 'faststone':
        args.fix = args.fix or 'faststone'
    elif args.fix:
        parser.error('--fix applies to faststone only')
    else:
        args.fix = args.app
    if args.values and args.command not in ('set', 'assoc', 'wm-restore'):
        parser.error('key=value pairs require set')
    if app_args and args.command != 'run':
        parser.error('application arguments require run')
    prefix = args.prefix.resolve(strict=True)
    if not (prefix / 'system.reg').is_file():
        raise Error('Not an existing Wine prefix')
    if args.command == 'wm-restore':  # internal, started by free_alt_click; never takes the lock
        restore_alt_click(prefix, args.app, int(args.values[0]))
        return
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
        elif args.command == 'logs':
            out, count = logs_bundle(prefix, args.app)
            print('✓ ' + str(out) + ' (' + str(count) + ' run logs); send this file')
        elif args.command == 'assoc':
            _, state = read_state(prefix, args.exe, args.app)
            assoc(prefix, args.app, state, args.values)
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
                      ' contrast=1.0..4.0 scaling=exact|smooth alt-click=app|desktop tahoma=' + '|'.join(SETTINGS['tahoma']) + ' scanner=off|on system=raster|tahoma logs=on|off)')
                print('  Launch: dllmgr run ' + args.app)
                for pid, kind in running_on(Path(state['exe']).name):
                    print('  Running: pid ' + str(pid) + ' on the ' + kind)
                log = prefix / LAUNCH_LOG
                last = [l for l in log.read_text(errors='replace').splitlines() if ' run ' + args.app + ':' in l][-2:] if log.is_file() else []
                for line in last:
                    print('  Last launches: ' + line if line is last[0] else '                 ' + line)
                for line in trampoline_summary(prefix):
                    print('  ' + line)
        else:
            try:
                watched = launch(args, prefix)
            except BaseException as error:
                launch_log(prefix, 'run ' + args.app + ': failed: ' + (str(error) or type(error).__name__))
                raise
    if args.command == 'run' and watched:
        if watched_run():
            watch(prefix, args.app, *watched)
        else:
            sys.exit(supervise(prefix, args.app, *watched) & 0xff)


if __name__ == '__main__':
    try:
        main()
    except (Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('dllmgr: ' + str(error), file=sys.stderr)
        sys.exit(1)
