#!/usr/bin/env python3
import os,json,time,subprocess as sp,signal,traceback
from pathlib import Path
b=Path('/workspace/work/photoshop-cs2');ctl=b/'control';ev=b/'evidence'
for d in [ctl/'requests',ctl/'responses',ev]:d.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(WINEPREFIX=str(b/'prefix110'),WINEARCH='win32',WINEDEBUG='fixme-all')
processes=[];logs=[]
def record(obj):
 obj['utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 with (ev/'actions.jsonl').open('a') as f:f.write(json.dumps(obj)+'\n')
def launch(argv,name):
 log=(ev/(name+'.log')).open('w');logs.append(log)
 p=sp.Popen(argv,env=env,stdout=log,stderr=sp.STDOUT,start_new_session=True);processes.append(p)
 record({'launch':argv,'pid':p.pid,'log':name+'.log'});return p
def run(argv,name,timeout=300):
 p=launch(argv,name);code=p.wait(timeout);record({'exit':name,'code':code});return code
try:
 if run(['wine','wineboot','--init'],'wineboot',900):raise RuntimeError('wineboot failed')
 if run(['wine','reg','add',r'HKCU\Control Panel\Desktop','/v','LogPixels','/t','REG_DWORD','/d','192','/f'],'dpi',180):raise RuntimeError('DPI failed')
 (ctl/'ready.json').write_text(json.dumps({'prefix':env['WINEPREFIX'],'display':env['DISPLAY'],'wine':'11.0','dpi':192,'kernel':os.uname().release}))
 record({'state':'ready'})
 while True:
  for path in sorted((ctl/'requests').glob('*.json')):
   dest=ctl/'responses'/path.name
   if dest.exists():continue
   req=json.loads(path.read_text());res={'request':req}
   try:
    action=req['action'];stamp=path.stem
    if action=='stop':res['ok']=True;dest.write_text(json.dumps(res));raise SystemExit(0)
    elif action=='launch':
     p=launch(req['argv'],stamp);res.update(ok=True,pid=p.pid)
    elif action=='run':
     code=run(req['argv'],stamp,req.get('timeout',180));res.update(ok=code==0,code=code,output=(ev/(stamp+'.log')).read_text(errors='replace'))
    elif action=='snapshot':
     image=ev/(req['name']+'.png');code=run(['import','-window','root',str(image)],stamp,120)
     tree=sp.run(['xwininfo','-root','-tree'],env=env,capture_output=True,text=True,timeout=30)
     (ev/(req['name']+'-xwindows.txt')).write_text(tree.stdout+tree.stderr)
     res.update(ok=code==0,image=str(image),tree=tree.stdout)
    elif action=='status':
     ps=sp.run(['ps','-eo','pid,stat,comm,wchan:30'],capture_output=True,text=True)
     res.update(ok=True,processes=ps.stdout,children=[{'pid':p.pid,'returncode':p.poll()} for p in processes])
    else:raise ValueError(action)
   except Exception:res.update(ok=False,error=traceback.format_exc())
   record(res);dest.write_text(json.dumps(res))
  time.sleep(.2)
except Exception:
 (ev/'controller-error.txt').write_text(traceback.format_exc());raise
finally:
 sp.run(['wineserver','-k'],env=env,timeout=15)
 for p in reversed(processes):
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
 for log in logs:log.close()
