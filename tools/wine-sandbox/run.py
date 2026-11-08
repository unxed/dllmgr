#!/usr/bin/env python3
"""Run a Wine job in the prepared CPU-emulated Linux VM."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess as sp
import sys
import time

base = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--smoke', action='store_true')
ap.add_argument('--arch', choices=['win32', 'win64'], default='win32')
ap.add_argument('--timeout', type=int, default=600, help='guest command/first wineboot timeout in seconds')
ap.add_argument('command', nargs=argparse.REMAINDER, help='command after --; executes with private Wine and DISPLAY')
args = ap.parse_args()
command = args.command[1:] if args.command[:1]==['--'] else args.command
if args.smoke == bool(command):
    ap.error('choose --smoke or a command after --')
if args.timeout < 1:
    ap.error('--timeout must be positive')
lock = (base/'run.lock').open('w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    ap.error('another job owns this stand; use another --state for concurrency')
cfg = json.loads((base/'stand.json').read_text())
artifacts = base/'artifacts'
artifacts.mkdir(exist_ok=True)
result_path = artifacts/'result.json'
result_path.unlink(missing_ok=True)
(base/'job.json').write_text(json.dumps({'smoke': args.smoke, 'arch': args.arch,
                                       'command': command, 'timeout': args.timeout}, indent=2)+'\n')
root = base/'root'
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = str(root/'usr/lib/x86_64-linux-gnu')
qmp = base/'qmp.sock'
qmp.unlink(missing_ok=True)
argv = [str(root/'usr/bin/qemu-system-x86_64'), '-machine', 'pc,accel=tcg,smm=off',
        '-cpu', 'qemu64', '-smp', '1', '-m', '1024', '-nodefaults', '-display', 'none',
        '-serial', 'stdio', '-qmp', f'unix:{qmp},server=on,wait=off', '-no-reboot',
        '-L', str(root/'usr/share/qemu'), '-bios', str(root/'usr/share/seabios/bios-256k.bin'),
        '-kernel', cfg['kernel'], '-initrd', str(base/'initramfs.cpio.gz'),
        '-append', 'console=ttyS0,115200 earlyprintk=serial,ttyS0,115200 panic=-1 loglevel=4',
        '-fsdev', 'local,id=hostroot,path=/,security_model=none,readonly=on,multidevs=remap',
        '-device', 'virtio-9p-pci,fsdev=hostroot,mount_tag=hostroot',
        '-fsdev', f'local,id=work,path={cfg["workspace"]},security_model=none,multidevs=remap',
        '-device', 'virtio-9p-pci,fsdev=work,mount_tag=work',
        '-fsdev', f'local,id=runtime,path={root},security_model=none,readonly=on,multidevs=remap',
        '-device', 'virtio-9p-pci,fsdev=runtime,mount_tag=runtime']
started = time.monotonic()
with (artifacts/'serial.log').open('w') as log:
    process = sp.Popen(argv, env=env, stdout=log, stderr=sp.STDOUT, start_new_session=True)
    (base/'vm.pid').write_text(str(process.pid)+'\n')
    try:
        process.wait(timeout=args.timeout+300)
    except (sp.TimeoutExpired, KeyboardInterrupt):
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except sp.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        print('VM stopped; inspect artifacts/serial.log and result.json', file=sys.stderr)
        raise SystemExit(1)
    finally:
        (base/'vm.pid').unlink(missing_ok=True)
        qmp.unlink(missing_ok=True)
if not result_path.exists():
    print('No completed guest result; inspect '+str(artifacts/'serial.log'), file=sys.stderr)
    raise SystemExit(1)
result = json.loads(result_path.read_text())
result['elapsed_seconds'] = round(time.monotonic()-started, 1)
result_path.write_text(json.dumps(result, indent=2)+'\n')
print(('PASS' if result['ok'] else 'FAIL')+': '+str(result_path))
if not result['ok']:
    print(result.get('error', 'Guest failed'), file=sys.stderr)
raise SystemExit(0 if result['ok'] else 1)
