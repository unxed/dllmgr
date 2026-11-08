#!/usr/bin/env python3
"""Build a tiny initramfs from verified Debian packages in the stand."""
import gzip
import json
import lzma
from pathlib import Path
import shlex
import shutil
import subprocess as sp

base = Path(__file__).resolve().parent
cfg = json.loads((base/'stand.json').read_text())
ram = base/'initramfs'
for directory in ['bin', 'dev', 'proc', 'sys', 'mnt', 'modules', 'tmp']:
    (ram/directory).mkdir(parents=True, exist_ok=True)
shutil.copy2(base/'root/usr/bin/busybox', ram/'bin/busybox')
for name in ['sh', 'mount', 'mkdir', 'chmod', 'insmod', 'chroot', 'poweroff', 'cat', 'ip']:
    path = ram/'bin'/name
    if not path.exists():
        path.symlink_to('busybox')
modules = {p.name.removesuffix('.ko.xz').replace('-', '_'): p
           for p in (base/'kernel/usr/lib/modules').rglob('*.ko.xz')}
builtins = next((base/'kernel/usr/lib/modules').glob('*/modules.builtin')).read_text()
builtin_names = {Path(line).name.removesuffix('.ko').replace('-', '_')
                 for line in builtins.splitlines()}
order = []


def add_module(name):
    if name in order or name in builtin_names:
        return
    data = lzma.decompress(modules[name].read_bytes())
    depends = next((x[8:].decode() for x in data.split(b'\0')
                    if x.startswith(b'depends=')), '')
    for dep in filter(None, depends.split(',')):
        add_module(dep.replace('-', '_'))
    (ram/'modules'/f'{name}.ko').write_bytes(data)
    order.append(name)


for name in ['virtio_pci', '9pnet_virtio', '9p']:
    add_module(name)
workspace = shlex.quote('/mnt'+cfg['workspace'])
guest = shlex.quote(str(base/'guest.py'))
init = '''#!/bin/sh
set -eu
export PATH=/bin
trap 'echo VM_BOOT_ERROR; poweroff -f' EXIT
mount -t proc proc /proc
mount -t sysfs sys /sys
mount -t devtmpfs dev /dev
mkdir -p /dev/pts /dev/shm
mount -t devpts devpts /dev/pts
mount -t tmpfs tmpfs /dev/shm
ip link set lo up
'''
init += ''.join(f'insmod /modules/{name}.ko\n' for name in order)
init += f'''mount -t 9p -o trans=virtio,version=9p2000.L,cache=loose,ro hostroot /mnt
mount -t 9p -o trans=virtio,version=9p2000.L work {workspace}
mount -t 9p -o trans=virtio,version=9p2000.L,cache=loose,ro runtime {shlex.quote('/mnt'+str(base/'root'))}
mount -t tmpfs tmpfs /mnt/tmp
mount -t tmpfs tmpfs /mnt/run
mount --bind /dev /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys /mnt/sys
mkdir -p /mnt/tmp/.X11-unix
chmod 1777 /mnt/tmp /mnt/tmp/.X11-unix
chroot /mnt /usr/bin/setpriv --reuid={cfg['uid']} --regid={cfg['gid']} --clear-groups /usr/bin/python3 {guest} || echo VM_TASK_FAILED
trap - EXIT
poweroff -f
'''
(ram/'init').write_text(init)
(ram/'init').chmod(0o755)
files = [str(p.relative_to(ram)) for p in ram.rglob('*')]
archive = sp.run([str(ram/'bin/busybox'), 'cpio', '-o', '-H', 'newc'],
                 input=('\n'.join(files)+'\n').encode(), cwd=ram,
                 capture_output=True, check=True).stdout
(base/'initramfs.cpio.gz').write_bytes(gzip.compress(archive, mtime=0))
print('Initramfs modules: '+', '.join(order))
