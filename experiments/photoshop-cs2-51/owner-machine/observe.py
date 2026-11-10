"""Run one stock launch and timestamp stderr/window observations on the stand."""
import os
from pathlib import Path
import subprocess
import threading
import time

root = Path('/tmp/opencode/opencode-owner-51a7')
assert os.environ['WINEPREFIX'] == str(root / 'prefix')
assert os.environ['DISPLAY'] == ':151'
step = os.environ.get('STEP', 'step2')
assert step in ('step2', 'step3', 'step4')
out = root / step
out.mkdir(exist_ok=True)
ps = root / 'prefix/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2'
env = dict(os.environ, XDG_DATA_HOME=str(root / 'data'), DLLMGR27_DEBUG='1')
if step == 'step3':
    env['DLLMGR27_NO_TRAMPOLINE'] = '1'
if step == 'step4':
    # Trace only Wine's builtin API implementations, never native MS DLLs.
    include = ';'.join(('kernel32.CreateMutexA', 'kernel32.CreateMutexW',
                        'kernel32.OpenMutexW', 'user32.FindWindowA',
                        'user32.FindWindowW', 'user32.SendMessageA',
                        'user32.SendMessageW', 'kernel32.ExitProcess',
                        'kernel32.GetModuleFileNameW', 'kernel32.LoadLibraryA'))
    subprocess.run(['/opt/wine-stable/bin/wine', 'reg', 'add',
                    r'HKCU\Software\Wine\Debug', '/v', 'RelayInclude',
                    '/d', include, '/f'], env=env, check=True)
    subprocess.run(['/opt/wine-stable/bin/wineserver', '-k'], env=env)
    time.sleep(2)
    env['WINEDEBUG'] = '+relay,+loaddll'
start = time.monotonic()
with (out / 'stock-timed.log').open('w') as log:
    process = subprocess.Popen(['/opt/wine-stable/bin/wine', 'Photoshop.exe'],
                               cwd=ps, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    def reader():
        for line in process.stdout:
            log.write(f'{time.monotonic() - start:.3f} ' + line.decode(errors='replace'))
            log.flush()
    threading.Thread(target=reader, daemon=True).start()
    with (out / 'windows-timed.log').open('w') as windows:
        previous = None
        for _ in range(225):
            listing = subprocess.run(['wmctrl', '-lx'], capture_output=True, text=True).stdout
            if listing != previous:
                windows.write(f'{time.monotonic() - start:.3f}\n{listing}')
                windows.flush()
                previous = listing
            time.sleep(.2)
    if step == 'step3':
        private_env = dict(os.environ, XDG_DATA_HOME=str(root / 'data'), WINEDEBUG='+loaddll,+process')
        before = time.monotonic()
        with (out / 'private.log').open('w') as private_log:
            result = subprocess.run(['dllmgr', 'run', 'photoshop-cs2', '--prefix', str(root / 'prefix')],
                                    env=private_env, stdout=private_log, stderr=subprocess.STDOUT, timeout=90)
        (out / 'private-result.txt').write_text(f'exit={result.returncode} duration={time.monotonic()-before:.3f}s\n')
    result = subprocess.run(['dllmgr', 'status', 'photoshop-cs2', '--prefix', str(root / 'prefix')],
                            env=env, capture_output=True, text=True)
    (out / 'status.txt').write_text(result.stdout + result.stderr)
    for name in ('launch.log', 'trampoline-run.log'):
        source = root / 'prefix/.dllmgr' / name
        if source.exists():
            (out / name).write_bytes(source.read_bytes())
