#!/usr/bin/env python3
"""dllmgr upgrade: re-apply the fixes of every app dllmgr has fixed whose
installed Wine runtime, module release or dllmgr revision differs from what
this dllmgr pins (like `apt dist-upgrade`; docs/concept.md §10).

Each app is re-applied exactly as `dllmgr fix <app>` does (scripts/private-app.py
install, transactional per app) with its recorded executable, prefix, recipe
and base Wine; `dllmgr set` settings live apart and stay. A failure is reported
and the next app is still tried.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import catalog_fixes  # noqa: E402
import update  # noqa: E402

_spec = importlib.util.spec_from_file_location('private_app', HERE / 'private-app.py')
private_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(private_app)

WINE = 'wine-11.0'
STALE_DAYS = 7


def short(value):
    return value[:7] if value else 'unknown'


def pinned_runtime():
    config = json.loads((HERE / 'private-runtime.json').read_text())
    return config.get('sha256'), private_app.runtime_release(None)


def entries(prefix):
    """(app, state path, state or None, problem) for every app journal in prefix."""
    found = []
    for app in sorted(private_app.PROFILES):
        for path in private_app.state_paths(prefix, app):
            try:
                if path.is_symlink():
                    raise ValueError('symlink journal')
                state = json.loads(path.read_text())
                if not isinstance(state, dict) or not state.get('exe') or not state.get('fix'):
                    raise ValueError('incomplete journal')
                found.append((app, path, state, None))
            except (OSError, ValueError) as error:
                found.append((app, path, None, 'unreadable ' + path.name + ' (' + str(error) + ')'))
    return found


def plan_for(app, state, revision):
    """What differs between the installed fix and this dllmgr's pins."""
    changes = []
    if state.get('phase') != 'installed':
        changes.append('finish an interrupted fix (phase ' + str(state.get('phase')) + ')')
    sha, release = pinned_runtime()
    if state.get('package_sha256') != sha:
        changes.append('runtime ' + state.get('runtime_release', 'unknown') + ' (sha256 ' +
                       str(state.get('package_sha256', '?'))[:12] + ') -> ' + release + ' (sha256 ' + str(sha)[:12] + ')')
    if private_app.PROFILES[app]['modules']:
        modules = catalog_fixes.release(state['fix'], WINE)
        if state.get('release') != modules:
            changes.append('modules ' + str(state.get('release') or 'none') + ' -> ' + modules)
    if revision and state.get('dllmgr_revision') != revision:
        changes.append('dllmgr ' + (short(state.get('dllmgr_revision')) if state.get('dllmgr_revision')
                                    else 'unknown (fixed by an older dllmgr)') + ' -> ' + short(revision))
    return changes


def process_prefix(pid, proc=Path('/proc')):
    """The Wine prefix a process runs in (its WINEPREFIX, else HOME/.wine), or
    None when its environment cannot be read."""
    try:
        env = dict(item.split(b'=', 1) for item in (proc / str(pid) / 'environ').read_bytes().split(b'\0') if b'=' in item)
    except OSError:
        return None
    value = env.get(b'WINEPREFIX') or (env[b'HOME'] + b'/.wine' if env.get(b'HOME') else None)
    return Path(os.fsdecode(value)).resolve() if value else None


def running_in(prefix, exe_name):
    """Pids of exe_name running in this prefix (unknown prefix counts: safe side)."""
    pids = []
    for pid, _ in private_app.running_on(exe_name):
        where = process_prefix(pid)
        if where is None or where == Path(prefix).resolve():
            pids.append(pid)
    return pids


def held_back(app, state):
    """Why an app that needs an upgrade must not be touched now, or None."""
    if str(state.get('runtime_release', '')).startswith('local package'):
        return ('installed from a local runtime package; re-run dllmgr fix ' + app +
                ' --runtime-package PATH yourself to keep it, or without it to switch to the pinned runtime')
    exe = Path(state['exe'])
    if not exe.is_file():
        return 'executable is gone: ' + str(exe) + ' (dllmgr fix ' + app + ' --exe PATH selects another)'
    running = running_in(state['prefix'], exe.name)
    if running:
        return ('running (pid ' + ', '.join(str(pid) for pid in running) +
                '); close it and run dllmgr upgrade again')
    return None


def reapply(app, prefix, state):
    """`dllmgr fix <app>` for the recorded installation; output goes to the terminal."""
    command = [sys.executable, str(HERE / 'private-app.py'), 'install', '--app', app,
               '--prefix', str(prefix), '--exe', state['exe']]
    if app == 'faststone':
        command += ['--fix', state['fix']]
    if state.get('base'):
        command += ['--base-wine', state['base']]
    return subprocess.run(command).returncode


def stale_note(now=None):
    stamp = update.read_stamp()
    if stamp is None:
        return ('Note: `dllmgr update` has not been run here; the plan uses the pins of this dllmgr (' +
                short(private_app.dllmgr_revision()) + '). Run `dllmgr update` first to get the latest.')
    days = int(((now or time.time()) - stamp['time']) // 86400)
    if days >= STALE_DAYS:
        return 'Note: `dllmgr update` was last run ' + str(days) + ' days ago; run it first to get the latest pins.'
    return None


def ask(question):
    try:
        return input(question).strip().lower() in ('y', 'yes')
    except EOFError:
        print()
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(prog='dllmgr upgrade', description=__doc__.split('\n\n')[0])
    parser.add_argument('--yes', action='store_true', help='apply the plan without asking')
    parser.add_argument('--dry-run', action='store_true', help='only print the plan')
    parser.add_argument('--prefix', type=Path, action='append',
                        help='Wine prefix to upgrade (repeatable; default: WINEPREFIX or ~/.wine)')
    args = parser.parse_args(argv)
    prefixes = args.prefix or [Path(os.environ.get('WINEPREFIX') or Path.home() / '.wine')]
    note = stale_note()
    if note:
        print(note)
    revision = private_app.dllmgr_revision()
    todo, failed = [], []
    current = held = 0
    for given in prefixes:
        prefix = given.resolve()
        if not (prefix / 'system.reg').is_file():
            if args.prefix:
                print('! ' + str(given) + ': not a Wine prefix')
                failed.append(str(given))
            else:
                print('· No Wine prefix at ' + str(given) + '; nothing to upgrade.')
            continue
        print('Prefix ' + str(prefix))
        found = entries(prefix)
        if not found:
            print('  · no apps fixed by dllmgr here')
        for app, path, state, problem in found:
            if problem:
                print('  ! ' + app + ': ' + problem)
                failed.append(app + ' in ' + str(prefix))
                continue
            name = app + '  ' + state.get('target', state['exe'])
            try:
                changes = plan_for(app, state, revision)
            except (KeyError, ValueError, OSError) as error:
                print('  ! ' + name + ': cannot compute the plan (' + str(error) + ')')
                failed.append(app + ' in ' + str(prefix))
                continue
            if not changes:
                print('  ✓ ' + name + ': up to date')
                current += 1
                continue
            reason = held_back(app, state)
            if reason:
                print('  ! ' + name + ': held back: ' + reason)
                held += 1
                continue
            print('  ↑ ' + name)
            for line in changes:
                print('      ' + line)
            todo.append((app, prefix, state))
    print(str(len(todo)) + ' to upgrade, ' + str(current) + ' up to date, ' + str(held) + ' held back' +
          (', ' + str(len(failed)) + ' with errors' if failed else '') + '.')
    if not todo or args.dry_run:
        return 1 if failed else 0
    if not args.yes and not ask('Re-apply ' + str(len(todo)) + ' fix' + ('es' if len(todo) > 1 else '') + '? [y/N] '):
        print('Nothing changed.')
        return 1 if failed else 0
    done = []
    for app, prefix, state in todo:
        print()
        print('› Upgrading ' + app + ' in ' + str(prefix))
        code = reapply(app, prefix, state)
        if code == 0:
            try:
                _, after = private_app.read_state(prefix, Path(state['exe']), app)
                left = plan_for(app, after, revision)
            except (private_app.Error, OSError, ValueError, KeyError) as error:
                left = ['journal unreadable after the fix: ' + str(error)]
            if left:
                print('! ' + app + ': re-applied, but it still differs from the pins: ' + '; '.join(left))
                code = 'check'
        if code == 0:
            done.append(app)
        else:
            if code != 'check':
                print('! ' + app + ': upgrade failed (exit ' + str(code) + '); its previous fix stays in place')
            failed.append(app + ' in ' + str(prefix))
    print()
    print(('✓ ' if not failed else '! ') + 'Upgraded: ' + (', '.join(done) or 'none') +
          ('; failed: ' + ', '.join(failed) if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)  # keep order with the fix's own output
    try:
        sys.exit(main())
    except (private_app.Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('dllmgr: ' + str(error), file=sys.stderr)
        sys.exit(1)
