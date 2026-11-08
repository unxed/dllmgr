#!/usr/bin/env python3
"""dllmgr diag: one read-only report with everything needed to debug a fix.

Prints short `key: value` lines (paste them into the issue). Read-only: it
never changes the prefix, Wine or the fix. Sections:
  dllmgr / wine     versions, install path, pinned runtime
  session           X11/Wayland, desktop, WM name, compositor on/off, screen
  prefix            WINEPREFIX, Wine DPI (LogPixels) from the registry files
  faststone         `status --json` of the private fix
  runtimes          cached private runtimes and their overlay modules
  processes         running FSViewer.exe: loaded win32u/winex11/ntdll .so
                    and the DLLMGR_*/WINELOADER environment it got
Usage: dllmgr diag [--prefix PATH]
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def out(key, value):
    print(f"{key}: {value}")


def short_sha(path):
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as stream:
            for block in iter(lambda: stream.read(1 << 20), b''):
                h.update(block)
        return h.hexdigest()[:12]
    except OSError as error:
        return f"unreadable ({error.strerror})"


def run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        return f"failed: {error}"


def section_dllmgr():
    out('dllmgr.path', HERE.parent)
    out('dllmgr.git', run(['git', '-C', str(HERE.parent), 'log', '-1', '--format=%h %cs %s']) or 'not a git checkout')
    try:
        pin = json.loads((HERE / 'private-runtime.json').read_text())
        out('runtime.pin', pin.get('url', '?').rsplit('/download/', 1)[-1] + ' sha ' + pin.get('sha256', '?')[:12])
    except (OSError, ValueError) as error:
        out('runtime.pin', f'unreadable ({error})')
    out('wine.opt', run(['/opt/wine-stable/bin/wine', '--version']) or 'missing')
    out('wine.path', run(['sh', '-c', 'command -v wine; wine --version']).replace('\n', ' '))


def x11_info():
    """WM name, compositor and screen size through libX11 (no extra tools)."""
    name = ctypes.util.find_library('X11')
    if not name or not os.environ.get('DISPLAY'):
        return {'x11': 'unavailable (no libX11 or DISPLAY)'}
    x = ctypes.CDLL(name)
    x.XOpenDisplay.restype = ctypes.c_void_p
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]
    dpy = x.XOpenDisplay(None)
    if not dpy:
        return {'x11': 'cannot open DISPLAY ' + os.environ['DISPLAY']}
    info = {}
    x.XDefaultScreen.argtypes = [ctypes.c_void_p]
    x.XRootWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XRootWindow.restype = ctypes.c_ulong
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x.XInternAtom.restype = ctypes.c_ulong
    x.XGetSelectionOwner.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    x.XGetSelectionOwner.restype = ctypes.c_ulong
    x.XDisplayWidth.argtypes = x.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
                                     ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong),
                                     ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ulong),
                                     ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p)]
    x.XFree.argtypes = [ctypes.c_void_p]
    screen = x.XDefaultScreen(dpy)
    root = x.XRootWindow(dpy, screen)
    info['screen'] = f"{x.XDisplayWidth(dpy, screen)}x{x.XDisplayHeight(dpy, screen)}"
    cm = x.XGetSelectionOwner(dpy, x.XInternAtom(dpy, f"_NET_WM_CM_S{screen}".encode(), 0))
    info['compositor'] = 'on' if cm else 'off'

    def prop(window, atom_name, kind):
        actual, fmt, n, after, data = ctypes.c_ulong(), ctypes.c_int(), ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_void_p()
        atom = x.XInternAtom(dpy, atom_name.encode(), 0)
        if x.XGetWindowProperty(dpy, window, atom, 0, 1024, 0, 0, ctypes.byref(actual), ctypes.byref(fmt),
                                ctypes.byref(n), ctypes.byref(after), ctypes.byref(data)) or not data.value:
            return None
        try:
            if kind == 'window':
                return ctypes.cast(data, ctypes.POINTER(ctypes.c_ulong))[0] if n.value else None
            return ctypes.string_at(data, n.value).decode('utf-8', 'replace')
        finally:
            x.XFree(data)

    wm = prop(root, '_NET_SUPPORTING_WM_CHECK', 'window')
    info['wm'] = (prop(wm, '_NET_WM_NAME', 'text') or 'unnamed') if wm else 'none (no EWMH WM)'
    return info


def section_session():
    for name in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'DISPLAY', 'WAYLAND_DISPLAY'):
        out('session.' + name, os.environ.get(name, '-'))
    try:
        for key, value in x11_info().items():
            out('session.' + key, value)
    except OSError as error:
        out('session.x11', f'error {error}')


def reg_value(path, key, name):
    """Value text of key\\name in a Wine .reg file (keys use doubled backslashes)."""
    try:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return None
    header = '[' + key.replace('\\', '\\\\').lower() + ']'
    inside = False
    for line in lines:
        if line.startswith('['):
            inside = line.lower().startswith(header)
        elif inside and line.lower().startswith('"' + name.lower() + '"='):
            return line.split('=', 1)[1].strip()
    return None


def section_prefix(prefix):
    out('prefix', prefix)
    out('prefix.initialized', (prefix / 'system.reg').is_file())
    hkcu = reg_value(prefix / 'user.reg', 'Control Panel\\Desktop', 'LogPixels')
    hklm = reg_value(prefix / 'system.reg', 'System\\ControlSet001\\Hardware Profiles\\Current\\Software\\Fonts',
                     'LogPixels')
    out('prefix.dpi', f"HKCU={hkcu or '-'} HKLM={hklm or '-'}")


def section_faststone(prefix):
    text = run([sys.executable, str(HERE / 'private-app.py'), 'status', '--json', '--prefix', str(prefix)])
    try:
        state = json.loads(text)
        out('faststone.target', state.get('target'))
        out('faststone.fix', state.get('fix'))
        out('faststone.runtime_package', str(state.get('runtime_package_sha256', state.get('package_sha256', '?')))[:12])
    except ValueError:
        out('faststone.status', (text or 'no output').splitlines()[-1][:200])


def section_runtimes():
    cache = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'dllmgr/runtimes'
    found = False
    for record in sorted(cache.glob('*/.dllmgr-runtime.json')):
        found = True
        runtime = record.parent
        try:
            state = json.loads(record.read_text())
        except (OSError, ValueError):
            out('runtime', f'{runtime.name[:12]} unreadable state')
            continue
        unix = runtime / 'lib/wine/x86_64-unix'
        mods = ' '.join(f"{m}={short_sha(unix / m)}" for m in ('win32u.so', 'winex11.so'))
        out('runtime', f"{runtime.name[:12]} package={state.get('package_sha256', '?')[:12]} {mods}")
    if not found:
        out('runtime', 'none cached in ' + str(cache))


def section_processes():
    seen = False
    for proc in sorted(Path('/proc').glob('[0-9]*'), key=lambda p: int(p.name)):
        try:
            cmd = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
        except OSError:
            continue
        if not cmd.strip().lower().split('.exe', 1)[0].endswith('fsviewer') or ' -c ' in cmd:
            continue
        try:
            maps = (proc / 'maps').read_text()
            env = (proc / 'environ').read_bytes().split(b'\0')
        except OSError:
            continue
        seen = True
        out('process', f"pid {proc.name}: {cmd.strip()[:160]}")
        for mod in ('ntdll.so', 'win32u.so', 'winex11.so'):
            paths = sorted({line.split()[-1] for line in maps.splitlines() if line.endswith('/' + mod)})
            out('process.' + mod, ' '.join(f"{p} ({short_sha(p)})" for p in paths) or 'not loaded')
        for item in env:
            item = item.decode('utf-8', 'replace')
            if item.startswith(('DLLMGR_', 'WINELOADER=', 'WINEPREFIX=', 'WINEDLLOVERRIDES=')):
                out('process.env', item[:200])
    if not seen:
        out('process', 'no FSViewer.exe running (start it and run diag again to see loaded modules)')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--prefix', type=Path, default=Path(os.environ.get('WINEPREFIX', str(Path.home() / '.wine'))))
    args = parser.parse_args()
    print('--- dllmgr diag ---')
    section_dllmgr()
    section_session()
    section_prefix(args.prefix.expanduser())
    section_faststone(args.prefix.expanduser())
    section_runtimes()
    section_processes()
    print('--- end ---')


if __name__ == '__main__':
    main()
