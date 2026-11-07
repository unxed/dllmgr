from pathlib import Path
import json,sys,fontforge
source,affected,directory=sys.argv[1:];out=Path(directory)
f=fontforge.open(source);reports=[]
for s in json.loads(Path(affected).read_text()):
 cp=int(s[2:],16);g=f[cp];before=g.validate(True);advance=g.width
 if before&12:
  g.correctDirection();g.removeOverlap();g.correctDirection();g.round()
 g.width=advance
 reports.append({'codepoint':s,'before':before,'after':g.validate(True)})
 (out/'progress.json').write_text(json.dumps(reports,indent=2))
f.generate(str(out/'generated.ttf'),flags=('no-hints',));f.close()
print('done',len(reports), 'self-intersections',sum(bool(r['after']&4) for r in reports))
