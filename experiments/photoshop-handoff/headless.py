import os
import pathlib
import signal
import subprocess
import sys
import time

base = pathlib.Path(__file__).resolve().parent
root = base.parent.parent
display = sys.argv[1] if len(sys.argv) > 1 else ':92'
env = {**os.environ, 'DISPLAY': display, 'WINEPREFIX': str(base / 'prefix110'),
       'WINEDEBUG': 'fixme-all', 'GSETTINGS_BACKEND': 'memory'}
children = []
log = (base / 'headless-session.log').open('a')
def launch(args):
    p = subprocess.Popen(args, env=env, stdout=log, stderr=log)
    children.append(p)
    return p
def cleanup(*_):
    for p in reversed(children):
        if p.poll() is None:
            p.terminate()
    sys.exit(0)
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)
x = launch([str(root/'work/headless/root/usr/bin/Xvfb'), display, '-screen', '0',
            '3072x1728x24', '-nolisten', 'tcp', '-dpi', '192'])
for _ in range(100):
    if x.poll() is not None:
        raise SystemExit('Xvfb failed: inspect headless-session.log')
    if pathlib.Path('/tmp/.X11-unix/X' + display[1:]).exists():
        break
    time.sleep(.05)
launch(['dbus-run-session', '--', 'muffin', '--sm-disable', '--x11'])
app = launch(['/opt/wine-stable/bin/wine', str(base/'prefix110/drive_c/Program Files (x86)/Adobe/Adobe Photoshop CS2/Photoshop.exe')])
(base/'live-session.txt').write_text(f'DISPLAY={display}\nWINEPREFIX={base / "prefix110"}\nrunner={os.getpid()}\nphotoshop={app.pid}\n')
print((base/'live-session.txt').read_text(), flush=True)
try:
    print('Photoshop exit:', app.wait(), flush=True)
finally:
    cleanup()
