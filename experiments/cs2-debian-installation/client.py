import sys,json,time
from pathlib import Path
b=Path('/workspace/work/photoshop-cs2/control');req=json.loads(sys.argv[1]);name=str(time.time_ns())+'.json'
(b/'requests').mkdir(exist_ok=True);(b/'requests'/name).write_text(json.dumps(req))
print('request',name,flush=True)
for i in range(3600):
 path=b/'responses'/name
 if path.exists():
  try:result=json.loads(path.read_text())
  except (json.JSONDecodeError,FileNotFoundError):time.sleep(.1);continue
  result.pop('tree',None);print(json.dumps(result));break
 time.sleep(.2)
else:raise SystemExit('no response')
