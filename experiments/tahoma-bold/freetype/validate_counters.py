#!/usr/bin/env python3
import json
from pathlib import Path
from collections import deque
import freetype
import argparse
parser=argparse.ArgumentParser(description="Preserve raster counter topology at 256 ppem, without hinting")
parser.add_argument('source',type=Path)
parser.add_argument('candidate',type=Path)
parser.add_argument('affected',type=Path)
args=parser.parse_args()
codes=[int(v[2:],16) for v in json.loads(args.affected.read_text())]
def holes(face,code):
 face.set_pixel_sizes(0,256);face.load_char(chr(code),freetype.FT_LOAD_RENDER|freetype.FT_LOAD_NO_HINTING|freetype.FT_LOAD_NO_AUTOHINT|freetype.FT_LOAD_NO_BITMAP)
 b=face.glyph.bitmap;w=b.width;h=b.rows;data=b.buffer;seen=set();sizes=[]
 for y in range(h):
  for x in range(w):
   if (x,y) in seen or data[y*b.pitch+x]>=128:continue
   q=[(x,y)];seen.add((x,y));area=0;border=False
   while q:
    xx,yy=q.pop();area+=1;border|=xx in (0,w-1) or yy in (0,h-1)
    for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
     if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and data[ny*b.pitch+nx]<128:
      seen.add((nx,ny));q.append((nx,ny))
   if not border and area>=4:sizes.append(area)
 return sorted(sizes)

source=freetype.Face(str(args.source));candidate=freetype.Face(str(args.candidate))
failures=[];ratios=[]
for code in codes:
 before,after=holes(source,code),holes(candidate,code)
 if len(before)!=len(after):
  failures.append((f'U+{code:04X}',before,after))
 elif before:
  ratios.extend(a/b for a,b in zip(after,before))
  if any(a < b*.1 for a,b in zip(after,before)):
   failures.append((f'U+{code:04X}',before,after))
print(f'Checked {len(codes)} affected glyphs; counter count / near-collapse failures: {len(failures)}')
for item in failures:print(item)
if ratios:print(f'Minimum retained counter area ratio: {min(ratios):.4f}')
print('This raster topology check does not establish visual font quality.')
raise SystemExit(bool(failures))
