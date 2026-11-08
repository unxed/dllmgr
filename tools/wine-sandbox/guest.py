#!/usr/bin/env python3
"""Execute one owned, invisible Wine/X11 job inside the VM."""
import json
import os
from pathlib import Path
import signal
import struct
import subprocess as sp
import time
import threading
import traceback

base = Path(__file__).resolve().parent
root = base/'root'
job = json.loads((base/'job.json').read_text())
artifacts = base/'artifacts'
artifacts.mkdir(exist_ok=True)
result_path = artifacts/'result.json'
result = {'ok': False, 'arch': job['arch'], 'checks': []}
env = os.environ.copy()
env.update(DISPLAY=':191', WINEPREFIX=str(base/('prefix-'+job['arch'])),
           WINEARCH=job['arch'], WINEDLLOVERRIDES='mscoree,mshtml=', WINEDEBUG='-all',
           WINESERVER=str(root/'opt/wine-stable/bin/wineserver'),
           LD_LIBRARY_PATH=str(root/'usr/lib/i386-linux-gnu')+':'+str(root/'usr/lib/x86_64-linux-gnu'),
           XDG_CACHE_HOME=str(base/'cache'), XDG_CONFIG_HOME=str(base/'config'),
           XDG_DATA_HOME=str(base/'data'), XDG_DATA_DIRS=str(root/'usr/share')+':/usr/share',
           PATH=str(root/'opt/wine-stable/bin')+':'+str(root/'usr/bin')+':/usr/bin:/bin')
for key in ['XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME']:
    Path(env[key]).mkdir(exist_ok=True)
wine = str(root/'opt/wine-stable/bin/wine')
xdotool = str(root/'usr/bin/xdotool')
processes = []
log = (artifacts/'processes.log').open('w')


def start(args):
    process = sp.Popen(args, env=env, stdout=log, stderr=log, start_new_session=True)
    processes.append(process)
    return process


def run(args, timeout=120):
    # File-backed output avoids waiting on pipes inherited by Wine descendants.
    index = len(result['checks'])
    out = artifacts/f'command-{index:03d}.stdout'
    err = artifacts/f'command-{index:03d}.stderr'
    with out.open('w') as stdout, err.open('w') as stderr:
        process = sp.Popen(args, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        processes.append(process)
        code = process.wait(timeout=timeout)
    entry = {'argv': list(map(str, args)), 'returncode': code,
             'stdout': out.read_text(errors='replace'), 'stderr': err.read_text(errors='replace')}
    result['checks'].append(entry)
    result_path.write_text(json.dumps(result, indent=2)+'\n')
    if code:
        raise RuntimeError(f'{args[0]} returned {code}: {entry["stderr"]}')
    return entry


def wait_until(predicate, timeout, message):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.5)
    raise RuntimeError(message)


def smoke():
    run([wine, 'wineboot', '--init'], timeout=job['timeout'])
    marker = run([wine, 'cmd', '/c', 'echo WINE_SANDBOX_OK'])
    if 'WINE_SANDBOX_OK' not in marker['stdout']:
        raise RuntimeError('cmd did not return expected text')
    run([wine, 'reg', 'add', r'HKCU\Control Panel\Desktop', '/v', 'LogPixels',
         '/t', 'REG_DWORD', '/d', '192', '/f'])
    run([wine, 'reg', 'query', r'HKCU\Control Panel\Desktop', '/v', 'LogPixels'])
    pe = root/'opt/wine-stable/lib/wine'/('i386-windows' if job['arch']=='win32' else 'x86_64-windows')/'notepad.exe'
    data = pe.read_bytes()
    machine = struct.unpack_from('<H', data, struct.unpack_from('<I', data, 0x3c)[0]+4)[0]
    expected_machine = 0x14c if job['arch']=='win32' else 0x8664
    if machine != expected_machine:
        raise RuntimeError(f'Wrong PE machine: {machine:#x}')
    result['pe_machine'] = hex(machine)
    textfile = Path(env['WINEPREFIX'])/'drive_c/sandbox-probe.txt'
    textfile.write_text('Synthetic sandbox probe.\r\n')
    start([wine, 'notepad', r'C:\sandbox-probe.txt'])
    def find_window():
        response = sp.run([xdotool, 'search', '--onlyvisible', '--class', 'notepad'],
                          env=env, capture_output=True, text=True, timeout=10)
        return response.stdout.splitlines()[0] if response.returncode==0 else None
    window = wait_until(find_window, 120, 'Notepad window not visible')
    def document_loaded():
        response = sp.run([xdotool, 'getwindowname', window], env=env, capture_output=True, text=True, timeout=10)
        return 'sandbox-probe' in response.stdout.casefold()
    wait_until(document_loaded, 120, 'Notepad has not finished opening the test document')
    run([xdotool, 'getwindowname', window])
    run([xdotool, 'windowactivate', '--sync', window])
    run([xdotool, 'windowfocus', '--sync', window])
    time.sleep(3)
    run(['import', '-window', 'root', str(artifacts/'before-input.png')])
    run([xdotool, 'key', '--clearmodifiers', 'ctrl+a'])
    text = 'Wine 11.0 '+job['arch']+': Xvfb input and save verified.'
    run([xdotool, 'type', '--clearmodifiers', text])
    run([xdotool, 'key', '--clearmodifiers', 'ctrl+s'])
    def saved():
        data = textfile.read_bytes()
        for encoding in ['utf-8-sig', 'utf-16']:
            try:
                if text in data.decode(encoding):
                    return True
            except UnicodeError:
                pass
        return False
    wait_until(saved, 30, 'UI input was not saved to the synthetic file')
    run(['import', '-window', 'root', str(artifacts/'smoke.png')])
    result['saved_text'] = text


def heartbeat():
    while True:
        snapshot = sp.run(['/usr/bin/ps', '-eo', 'pid,stat,comm,wchan:30'], capture_output=True, text=True)
        (artifacts/'live-processes.txt').write_text(snapshot.stdout)
        time.sleep(5)

threading.Thread(target=heartbeat, daemon=True).start()

try:
    result['wine_version'] = run([wine, '--version'])['stdout'].strip()
    result['kernel'] = os.uname().release
    start([str(root/'usr/bin/Xvfb'), ':191', '-screen', '0', '3072x1728x24',
           '-dpi', '192', '-nolisten', 'tcp'])
    wait_until(lambda: sp.run(['xdpyinfo'], env=env, stdout=sp.DEVNULL,
                             stderr=sp.DEVNULL, timeout=10).returncode==0,
               30, 'Xvfb failed')
    wm = start([str(root/'usr/bin/openbox'), '--sm-disable', '--config-file',
                str(root/'etc/xdg/openbox/rc.xml')])
    time.sleep(1)
    if wm.poll() is not None:
        raise RuntimeError('Openbox exited')
    if job['smoke']:
        smoke()
    else:
        run(job['command'], timeout=job['timeout'])
    result['ok'] = True
except Exception:
    result['error'] = traceback.format_exc()
    try:
        sp.run(['import', '-window', 'root', str(artifacts/'failure.png')], env=env, timeout=30, stdout=log, stderr=log)
    except (sp.TimeoutExpired, OSError):
        pass
finally:
    try:
        sp.run([str(root/'opt/wine-stable/bin/wineserver'), '-k'], env=env,
               stdout=log, stderr=log, timeout=15)
    except sp.TimeoutExpired:
        pass
    for process in reversed(processes):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except sp.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
    result_path.write_text(json.dumps(result, indent=2)+'\n')
    log.close()
print('WINE_SANDBOX_PASS' if result['ok'] else 'WINE_SANDBOX_FAIL', flush=True)
raise SystemExit(0 if result['ok'] else 1)
