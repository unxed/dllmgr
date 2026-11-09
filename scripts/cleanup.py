#!/usr/bin/env python3
"""dllmgr cleanup [FIX] [--prefix P]... [--dry-run] [--yes]

Remove the traces of dllmgr (owner request 2026-11-09, "for anxious people").

Without FIX: undo every recipe dllmgr installed in every prefix it can find,
remove its state directories in those prefixes, the runtime and helper
caches, its desktop entries and finally dllmgr itself (~/.local/lib/dllmgr and
the ~/.local/bin/dllmgr link). With FIX (faststone, photoshop-cs2,
faststone-avif, faststone-fonts): undo only that recipe everywhere, and drop
the private runtime cache when no application recipe uses it any more.

Prefixes: WINEPREFIX (or ~/.wine), every --prefix, and every Wine prefix under
the home directory (4 levels deep) that holds dllmgr state. Every recipe is
undone through its own `dllmgr unfix`, so original files and registry values
are restored the same way as by hand; nothing is removed when an undo fails.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
WRAPPER = HERE.parent / 'dllmgr'
APPS = ('faststone', 'photoshop-cs2')
FIXES = APPS + ('faststone-avif', 'faststone-fonts')
SKIP = {'.cache', '.git', 'node_modules', 'drive_c', 'dosdevices', '.npm', '.cargo', '.rustup', 'go'}


def home():
    return Path(os.environ.get('HOME', str(Path.home())))


def data_home():
    return Path(os.environ.get('XDG_DATA_HOME', str(home() / '.local/share')))


def has_state(prefix):
    return (prefix / '.dllmgr').is_dir() or (prefix / 'drive_c/dllmgr').is_dir()


def desktop_prefixes():
    """Prefixes named in dllmgr's routed launchers (they can live anywhere)."""
    out = []
    for entry in sorted((data_home() / 'applications').glob('dllmgr-*.desktop')):
        try:
            line = next((l for l in entry.read_text().splitlines() if l.startswith('Exec=')), '')
            words = shlex.split(line[5:])
        except (OSError, ValueError):
            continue
        if '--prefix' in words[:-1]:
            out.append(Path(words[words.index('--prefix') + 1]))
    return out


def find_prefixes(extra, depth=4):
    found = []
    first = Path(os.environ.get('WINEPREFIX', str(home() / '.wine')))
    for p in [first, *extra, *desktop_prefixes()]:
        if (p / 'system.reg').is_file() and p.resolve() not in [f.resolve() for f in found]:
            found.append(p)
    base = home()
    for root, dirs, files in os.walk(base):
        rel = Path(root).relative_to(base)
        if 'system.reg' in files:
            p = Path(root)
            if has_state(p) and p.resolve() not in [f.resolve() for f in found]:
                found.append(p)
            dirs[:] = []  # never walk into a prefix
            continue
        if len(rel.parts) >= depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d not in SKIP and not os.path.islink(os.path.join(root, d))]
    return found


def installed(prefix):
    """Recipes with dllmgr state in this prefix: [(fix, extra args)]."""
    state = prefix / '.dllmgr'
    out = []
    for app in APPS:
        for path in sorted((state / 'apps').glob(app + '-*.json')):
            try:
                exe = json.loads(path.read_text()).get('exe')
            except (OSError, ValueError):
                exe = None
            out.append((app, ['--exe', exe] if exe else []))
    if (state / 'avif-codec.json').is_file():
        out.append(('faststone-avif', []))
    if (state / 'tahoma-bold.json').is_file():
        out.append(('faststone-fonts', []))
    for path in sorted((state / 'prefill').glob('*.json')):
        try:
            exe = json.loads(path.read_text())['exe']
        except (OSError, ValueError, KeyError):
            continue
        out.append(('prefill-proxy', ['--exe', exe]))
    return out


def undo(prefix, fix, extra, dry):
    if fix == 'prefill-proxy':
        cmd = [sys.executable, str(HERE / 'prefill-proxy.py'), 'undo', '--prefix', str(prefix), *extra]
    else:
        cmd = [str(WRAPPER), 'unfix', fix, '--prefix', str(prefix), *extra]
    print('  unfix ' + fix + (' (' + extra[1] + ')' if extra else '') + ' in ' + str(prefix))
    if dry:
        return True
    env = dict(os.environ, WINEPREFIX=str(prefix))
    return subprocess.run(cmd, env=env).returncode == 0


def remove(path, dry):
    if not (path.exists() or path.is_symlink()):
        return
    print('  remove ' + str(path))
    if dry:
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def own_launcher():
    link = home() / '.local/bin/dllmgr'
    lib = home() / '.local/lib/dllmgr'
    if link.is_symlink() and str(os.readlink(link)).startswith(str(lib) + '/'):
        return link
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dllmgr cleanup', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('fix', nargs='?', choices=FIXES)
    parser.add_argument('--prefix', type=Path, action='append', default=[])
    parser.add_argument('--dry-run', action='store_true', help='only print what would be removed')
    parser.add_argument('--yes', action='store_true', help='do not ask')
    args = parser.parse_args(argv)

    prefixes = find_prefixes(args.prefix)
    print('dllmgr cleanup' + (' ' + args.fix if args.fix else ' (everything)') + (' — dry run' if args.dry_run else ''))
    print('Prefixes checked: ' + (', '.join(str(p) for p in prefixes) or 'none found'))
    if not args.dry_run and not args.yes:
        what = 'the ' + args.fix + ' recipe' if args.fix else 'all dllmgr recipes, caches and dllmgr itself'
        if input('Remove ' + what + '? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('Nothing changed.')
            return 1
    failed = []
    for p in prefixes:
        # application recipes first: undoing them also removes their launch
        # trampoline (a prefill proxy), so the rest is read again afterwards
        steps = [(f, e) for f, e in installed(p) if f in APPS and (not args.fix or f == args.fix)]
        failed += [p for f, e in steps if not undo(p, f, e, args.dry_run)]
        rest = [(f, e) for f, e in installed(p) if f not in APPS and (not args.fix or f == args.fix)]
        if args.dry_run:
            rest = [(f, e) for f, e in rest if not (f == 'prefill-proxy' and any(e == x for _, x in steps))]
        failed += [p for f, e in rest if not undo(p, f, e, args.dry_run)]
    if failed:
        print('dllmgr: some recipes could not be undone (see above); nothing else was removed.', file=sys.stderr)
        return 1
    if args.fix:
        if args.fix in APPS and not any(f in APPS for p in prefixes for f, _ in installed(p)):
            remove(data_home() / 'dllmgr/runtimes', args.dry_run)
        print('Done.' if not args.dry_run else 'Dry run: nothing changed.')
        return 0
    for p in prefixes:
        remove(p / '.dllmgr', args.dry_run)
        remove(p / 'drive_c/dllmgr', args.dry_run)
    remove(data_home() / 'dllmgr', args.dry_run)
    remove(home() / '.cache/fix-it-in-wine', args.dry_run)
    for entry in sorted((data_home() / 'applications').glob('dllmgr-*.desktop')):
        remove(entry, args.dry_run)
    launcher = own_launcher()
    remove(home() / '.local/lib/dllmgr', args.dry_run)
    if launcher:
        remove(launcher, args.dry_run)
    print('Done: dllmgr and everything it installed are gone.' if not args.dry_run else 'Dry run: nothing changed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
