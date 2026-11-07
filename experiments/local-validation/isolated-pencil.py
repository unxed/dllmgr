from pathlib import Path
import argparse, os, sys, subprocess, shutil, copy, importlib.util, json, hashlib
parser=argparse.ArgumentParser(description="Experimental isolated-pencil validation; restores the installed bundle in finally.")
for option in ('prefix','exe','image','settings','observer','output'):
 parser.add_argument('--'+option,type=Path,required=True)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[2]
root=args.output.resolve();root.mkdir(exist_ok=False)
prefix=args.prefix.resolve();config=args.settings.resolve()
shutil.copytree(config,root/'settings-before')
os.environ['DLLMGR_TOOLS']=os.environ['FIW_TOOLS']
os.environ['DLLMGR_WINE']='wine';os.environ['FIW_WINE']=str(repo/'scripts/wine-reg-utf8.py')
sys.path.insert(0,str(repo/'scripts'))
spec=importlib.util.spec_from_file_location('manager',repo/'scripts/manage-faststone.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
o=m.override
state=copy.deepcopy(o.load_state(str(prefix)))
entries=[e for e in state['entries'] if e['exe'].lower()=='fsviewer.exe']
assert len(entries)==2 and all(e.get('dllmgr_fix')=='faststone' for e in entries)
files=[m.snapshot(str(prefix),e['dest'],e['name']) for e in entries]
for e in entries:
 assert o.file_sha(e['dest'])==e['new_sha256']
 assert o.file_sha(e['backup'])==e['orig_sha256']
gdi=next(e for e in entries if o.norm(e['name'])=='gdiplus')
shutil.copy2(gdi['dest'],root/'gdiplus.dll')
plan=root/'gdiplus-only.json';plan.write_text(json.dumps([dict(dll=str(root/'gdiplus.dll'),name='gdiplus.dll',slot='system')]))
env=dict(os.environ,WINEPREFIX=str(prefix),WINEDEBUG='-all')
helper=[sys.executable,str(repo/'scripts/manage-faststone.py')]
app=args.exe.resolve()
observer=args.observer.resolve()
image=args.image.resolve()
def run(stage):
 out=root/stage;out.mkdir()
 with (out/'observations.txt').open('wb') as stdout,(out/'stderr.txt').open('wb') as stderr:
  subprocess.run(['wine',str(observer),str(app),str(image),'draw'],env=env,cwd=out,stdout=stdout,stderr=stderr,timeout=75,check=True)
 print(stage,'complete',flush=True)
try:
 subprocess.run(helper+['undo','--fix','faststone','--prefix',str(prefix)],env=env,check=True,stdout=(root/'undo.txt').open('w'))
 run('stock')
 subprocess.run(helper+['apply','--fix','winehq-48874','--prefix',str(prefix),'--plan',str(plan)],env=env,check=True,stdout=(root/'apply.txt').open('w'))
 run('gdiplus-only')
finally:
 m.restore(str(prefix),files,state)
 for p in (root/'settings-before').iterdir():
  if p.is_file():shutil.copy2(p,config/p.name)
 for f in files:
  assert o.file_sha(f['dest'])==hashlib.sha256(f['raw']).hexdigest()
  assert o.reg_query(str(prefix),'FSViewer.exe',o.norm(f['name']))==f['registry']
 assert o.load_state(str(prefix))==state
 (root/'restored.txt').write_text('Both installed DLLs, override registry values, managed state and original settings restored.\n')
 print('Original faststone-v2 state restored and verified.',flush=True)
