import subprocess as sp,json,sys
for req in json.loads(sys.argv[1]):
 r=sp.run([sys.executable,'/workspace/work/photoshop-cs2/control/client.py',json.dumps(req)],capture_output=True,text=True,check=True)
 lines=r.stdout.splitlines();data=json.loads(lines[-1]);print(json.dumps(data),flush=True)
 if not data.get('ok'):raise SystemExit(1)
