#!/usr/bin/env python3
"""Restore locked local MinGW tools and compile the public Win32 probes."""
import argparse,hashlib,json,os,shutil,subprocess as sp
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--root',type=Path,default=Path('/workspace/work/photoshop-cs2'))
a=ap.parse_args();root=a.root.resolve();here=Path(__file__).resolve().parent
cache=root/'toolchain/debs';tools=root/'toolchain/root';control=root/'control'
for path in [cache,tools,control,root/'evidence',control/'requests',control/'responses']:path.mkdir(parents=True,exist_ok=True)
for pkg in json.loads((here/'toolchain.json').read_text()):
 deb=cache/pkg['file']
 if not deb.exists() or hashlib.sha256(deb.read_bytes()).hexdigest()!=pkg['sha256']:
  temp=deb.with_suffix('.partial')
  sp.run(['curl','-fLsS','--retry','2','--max-time','300',pkg['url'],'-o',str(temp)],check=True)
  assert hashlib.sha256(temp.read_bytes()).hexdigest()==pkg['sha256'],pkg['file']
  temp.replace(deb)
 sp.run(['dpkg-deb','-x',str(deb),str(tools)],check=True)
for name in ['controller.py','client.py','sequence.py','launch-in-dir.py']:
 shutil.copy2(here/name,control/name)
env=os.environ.copy();env['PATH']=str(tools/'usr/bin')+':'+env['PATH']
compiler=tools/'usr/bin/i686-w64-mingw32-gcc-posix'
for name,libs in [('windows-install',['-luser32']),('dpi-probe',['-lgdi32','-luser32']),('product-state',['-lmsi']),('wait-exit',['-luser32'])]:
 shutil.copy2(here/(name+'.c'),control/(name+'.c'))
 temp=control/(name+'.new.exe');dest=control/(name+'.exe')
 sp.run([str(compiler),'-O2','-s',str(control/(name+'.c')),'-o',str(temp),*libs],env=env,check=True)
 temp.replace(dest)
shutil.copy2(control/'windows-install.exe',control/'windows.exe')
print('Local controls restored; no system installation. Start the prepared VM/controller separately.')
