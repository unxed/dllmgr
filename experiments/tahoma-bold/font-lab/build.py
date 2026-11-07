"""Prototype Wine Cyrillic bold correction; original advances are immutable."""
import json
import sys
from pathlib import Path
import fontforge
import psMat
from fontTools.ttLib import TTFont
from fontTools.pens.areaPen import AreaPen
source,original,regular,directory=sys.argv[1:]
out=Path(directory);out.mkdir(exist_ok=True)
b=TTFont(original);r=TTFont(regular);bc=b.getBestCmap();rc=r.getBestCmap();bg=b.getGlyphSet();rg=r.getGlyphSet();bad=[]
for cp in range(0x400,0x530):
 if cp not in bc or cp not in rc: continue
 p=AreaPen(rg);q=AreaPen(bg);rg[rc[cp]].draw(p);bg[bc[cp]].draw(q)
 if abs(p.value)>1 and .95<abs(q.value/p.value)<1.05: bad.append(cp)
f=fontforge.open(source)
for cp in bad:f[cp].unlinkRef()
for cp in bad:
 g=f[cp];advance=g.width;g.correctDirection();g.changeWeight(120,'LCG',0,0,'retain',1)
 x0,y0,x1,y1=g.boundingBox();width=x1-x0;limit=advance-32
 if width>limit:g.transform(psMat.scale(limit/width,1))
 x0,y0,x1,y1=g.boundingBox();g.transform(psMat.translate((advance-(x1-x0))/2-x0,0));g.width=advance
f.save(str(out/'tahomabd.sfd'))
f.generate(str(out/'generated.ttf'),flags=('no-hints',))
f.close()
n=TTFont(out/'generated.ttf');nc=n.getBestCmap()
for cp in bad:
 old,new=bc[cp],nc[cp];b['glyf'][old]=n['glyf'][new];advance=b['hmtx'][old][0];b['hmtx'][old]=(advance,n['hmtx'][new][1])
# Retain family/style selection; distinguish the corrected file/cache identity.
for name in b['name'].names:
 if name.nameID==5: name.string='Version 0.001; Cyrillic bold correction 1'.encode(name.getEncoding())
 if name.nameID==3: name.string='WineTahomaBold-Cyrillic-1'.encode(name.getEncoding())
 if name.nameID==6: name.string='WineTahomaBoldCyrillic'.encode(name.getEncoding())
b["head"].fontRevision=.002
b.recalcTimestamp=False
b.save(out/'tahomabd.ttf')
(out/'affected.json').write_text(json.dumps([f'U+{cp:04X}' for cp in bad],indent=2))
print('fixed',len(bad),''.join(map(chr,bad)))
