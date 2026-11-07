#!/usr/bin/env python3
"""Reproduce the experimental cleaned/hinted Tahoma Bold, no installation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from fontTools.ttLib import TTFont

here=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('wine_source',type=Path)
parser.add_argument('output',type=Path)
parser.add_argument('--ttfautohint',default='ttfautohint')
args=parser.parse_args()
source=args.wine_source.resolve()/'fonts/tahomabd.ttf'
out=args.output.resolve();out.mkdir(exist_ok=True,parents=True)
raw=out/'raw005.ttf';clean=out/'clean006.ttf';generated=out/'hinted-generated.ttf'
subprocess.run([sys.executable,str(here/'build_candidate.py'),str(source),str(here/'affected.json'),str(raw)],check=True,timeout=20)
subprocess.run(['fontforge','-lang=py','-script',str(here/'cleanup.py'),str(raw),str(here/'affected.json'),str(out)],check=True,timeout=20)
rows=json.loads((out/'progress.json').read_text())
if len(rows)!=66 or any(r['after']&12 for r in rows):raise SystemExit('Outline cleanup did not pass')
b=TTFont(raw);n=TTFont(out/'generated.ttf');original=TTFont(source)
bc,nc=b.getBestCmap(),n.getBestCmap();names=set()
for value in json.loads((here/'affected.json').read_text()):
 cp=int(value[2:],16);old,new=bc[cp],nc[cp];names.add(old)
 b['glyf'][old]=n['glyf'][new];b['hmtx'][old]=(b['hmtx'][old][0],n['hmtx'][new][1])
for name in set(b.getGlyphOrder())-names:
 assert b['glyf'][name].compile(b['glyf'])==original['glyf'][name].compile(original['glyf'])
assert all(b['hmtx'][name][0]==original['hmtx'][name][0] for name in b.getGlyphOrder())
b['head'].fontRevision=.006;b.recalcTimestamp=False;b.save(clean)
subprocess.run([args.ttfautohint,str(clean),str(generated)],check=True,timeout=30)
f=TTFont(generated);f['head'].fontRevision=.007
values={3:'WineTahomaBold-Cyrillic-clean-hints-7',5:'Version 0.007; cleaned FreeType bold and ttfautohint',6:'WineTahomaBoldCyrillicCleanHints007'}
for item in f['name'].names:
 if item.nameID in values:item.string=values[item.nameID].encode(item.getEncoding())
f.recalcTimestamp=False;f.save(out/'tahomabd-revision-007.ttf')
assert f['hmtx'].metrics==b['hmtx'].metrics
print('Experimental font built; not installed. Visual acceptance is still required.')
