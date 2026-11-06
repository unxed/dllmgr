"""Synthetic UI observations; mapped-window timings are not responsiveness claims."""
from pathlib import Path
import json
import os
import subprocess
import time

out = Path('snapshots85'); out.mkdir(exist_ok=True)

def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()

def window(pattern, timeout=20):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        result = subprocess.run(['xdotool','search','--onlyvisible','--name',pattern],capture_output=True,text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()[-1]
        time.sleep(.05)
    raise RuntimeError(f'window not found: {pattern}')

def snap(name):
    run('scrot', str(out / (name+'.png')))
    (out / (name+'.txt')).write_text(run('xwininfo','-root','-tree'))

log = open(out/'app.log','w')
start = time.monotonic()
p = subprocess.Popen(['wine','FSViewer85/FSViewer.exe','Z:'+str(Path('images/white.bmp').resolve()).replace('/','\\')], stdout=log,stderr=log)
window('FastStone')
results = {'dpi':os.environ['TEST_DPI'],'startup_to_mapped_window_seconds':time.monotonic()-start}
time.sleep(2); snap('01-open')
run('xdotool','mousemove','900','500','click','2'); time.sleep(1); snap('02-middle')
run('xdotool','click','2'); time.sleep(1); snap('03-middle-again')
for attempt in range(2):
    start = time.monotonic(); run('xdotool','key','d')
    draw = window('^Draw Board')
    results[f'draw_{attempt+1}_to_mapped_window_seconds'] = time.monotonic()-start
    time.sleep(1); snap(f'04-draw-{attempt+1}')
    run('xdotool','windowactivate','--sync',draw,'key','alt+F4')
    time.sleep(1)
(out/'timings.json').write_text(json.dumps(results,indent=2))
run('wineserver','-k')
p.wait(timeout=10)
