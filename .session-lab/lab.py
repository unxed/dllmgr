#!/usr/bin/env python3
"""Temporary #37 HTTPS command transport; not a project-wide execution policy."""
import argparse,base64,json,os,signal,subprocess as sp,time,traceback
from pathlib import Path

def api(path,data=None,method=None):
    argv=['gh','api','repos/'+os.environ.get('LAB_REPO','unxed/dllmgr')+'/'+path]
    if method:argv+=['--method',method]
    if data is not None:argv+=['--input','-']
    p=sp.run(argv,input=json.dumps(data) if data is not None else None,text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return json.loads(p.stdout) if p.stdout.strip() else None

def branch_head(branch):return api('git/ref/heads/'+branch)['object']['sha']
def publish(branch,files,message):
    parent=branch_head(branch)
    tree=api('git/trees',{'base_tree':api('git/commits/'+parent)['tree']['sha'],'tree':[
        {'path':name,'mode':'100644','type':'blob','sha':api('git/blobs',{'content':base64.b64encode(data).decode(),'encoding':'base64'})['sha']}
        for name,data in files.items()]})['sha']
    commit=api('git/commits',{'message':message+'\n\nAgent: codex-debian-8c42','tree':tree,'parents':[parent]})['sha']
    api('git/refs/heads/'+branch,{'sha':commit,'force':False},'PATCH')

def child_env():
    allowed={'PATH','HOME','USER','LANG','LC_ALL','DISPLAY','WINEPREFIX','WINEARCH','WINEDEBUG','WINEDLLOVERRIDES','TMPDIR','GSETTINGS_BACKEND','DBUS_SESSION_BUS_ADDRESS'}
    return {k:v for k,v in os.environ.items() if k in allowed or k.startswith('XDG_')}

def execute(req,out,children):
    action=req['action']; result={'action':action,'ok':True}
    if action in ('run','launch'):
        argv=req['argv']
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv):raise ValueError('argv must be a nonempty string list')
        log=(out/'command.log').open('wb')
        p=sp.Popen(argv,cwd=req.get('cwd'),env=child_env(),stdout=log,stderr=sp.STDOUT,start_new_session=True)
        children.append((p,log));result['pid']=p.pid
        if action=='run':
            try:result['code']=p.wait(timeout=min(300,max(1,int(req.get('timeout',120)))))
            except sp.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(5)
                except sp.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                result.update(code=p.returncode,timed_out=True)
            log.flush();result.update(ok=result['code']==0,output=(out/'command.log').read_text(errors='replace')[-160000:])
    elif action=='status':
        result['children']=[{'pid':p.pid,'returncode':p.poll()} for p,_ in children]
        result['output']=sp.check_output(['ps','-eo','pid,etime,stat,comm'],text=True)
    elif action=='snapshot':
        sp.run(['import','-window','root',str(out/'screen.png')],env=child_env(),check=True,timeout=30)
        result['windows']=sp.check_output(['xwininfo','-root','-tree'],env=child_env(),text=True)
    elif action=='stop':result['stop']=True
    else:raise ValueError('unknown action: '+action)
    return result

def serve(minutes):
    run=os.environ['GITHUB_RUN_ID'];bus='session-codex-8c42-'+run;out=Path(os.environ['LAB_OUT']);out.mkdir(parents=True,exist_ok=True)
    base=branch_head(os.environ.get('GITHUB_REF_NAME','main'))
    for suffix in ('cmd','out'):api('git/refs',{'ref':'refs/heads/'+bus+'-'+suffix,'sha':base})
    meta={'run':run,'bus':bus,'display':os.environ['DISPLAY'],'prefix':os.environ['WINEPREFIX'],'deadline_utc_epoch':time.time()+minutes*60,'scope':'Temporary session task37 only; native Ubuntu/Wine baseline'}
    publish(bus+'-out',{'lab-results/session.json':json.dumps(meta,indent=2).encode()},'Start temporary native Wine session #37')
    (out/'session.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta),flush=True);done=set();children=[];last=time.monotonic();stop=False
    try:
        while not stop and time.time()<meta['deadline_utc_epoch'] and time.monotonic()-last<1200:
            head=branch_head(bus+'-cmd');tree=api('git/trees/'+head+'?recursive=1')['tree']
            for entry in sorted(tree,key=lambda x:x['path']):
                path=entry['path']
                if not path.startswith('lab-requests/') or not path.endswith('.json') or path in done:continue
                done.add(path);last=time.monotonic();name=Path(path).stem;folder=out/name;folder.mkdir()
                try:
                    raw=api('git/blobs/'+entry['sha']);req=json.loads(base64.b64decode(raw['content']))
                    result=execute(req,folder,children)
                except Exception:result={'ok':False,'error':traceback.format_exc()}
                result['utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());(folder/'response.json').write_text(json.dumps(result,indent=2))
                files={'lab-results/'+name+'/response.json':(folder/'response.json').read_bytes()}
                if (folder/'screen.png').exists():files['lab-results/'+name+'/screen.png']=(folder/'screen.png').read_bytes()
                publish(bus+'-out',files,'Temporary Wine session result '+name)
                stop=result.get('stop',False)
            time.sleep(3)
    finally:
        sp.run(['import','-window','root',str(out/'final-screen.png')],env=child_env(),timeout=30)
        for p,log in reversed(children):
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
            log.close()

def request(run,req):
    bus='session-codex-8c42-'+run;name=str(time.time_ns());path='lab-requests/'+name+'.json'
    api('contents/'+path,{'message':'Temporary session command '+name+' [skip ci]','branch':bus+'-cmd','content':base64.b64encode(json.dumps(req).encode()).decode()},'PUT')
    print('request',name,flush=True);deadline=time.monotonic()+360
    while time.monotonic()<deadline:
        head=branch_head(bus+'-out');tree=api('git/trees/'+head+'?recursive=1')['tree'];wanted='lab-results/'+name+'/'
        found=[x for x in tree if x['path'].startswith(wanted)]
        if any(x['path']==wanted+'response.json' for x in found):
            dest=Path('lab-output')/run/name;dest.mkdir(parents=True,exist_ok=True)
            for entry in found:
                data=api('git/blobs/'+entry['sha']);raw=base64.b64decode(data['content']);(dest/Path(entry['path']).name).write_bytes(raw)
            result=json.loads((dest/'response.json').read_text());print(json.dumps(result,ensure_ascii=False));print('saved',dest);return
        time.sleep(3)
    raise TimeoutError('No result yet; request is retained and must not be replayed blindly: '+name)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    s=sub.add_parser('serve');s.add_argument('--minutes',type=int,default=60)
    q=sub.add_parser('request');q.add_argument('--run',required=True);q.add_argument('json')
    a=ap.parse_args()
    if a.command=='serve':serve(a.minutes)
    else:request(a.run,json.loads(a.json))
