"""Compare unhinted FreeType rasters on common baselines; no display required."""
import json
import math
from pathlib import Path
import freetype
from PIL import Image, ImageChops, ImageDraw

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "font-lab/candidate/tahomabd.ttf"
CLEAN = HERE / "tahomabd-clean-unhinted.ttf"
CP = [int(s[2:],16) for s in json.loads((SOURCE.parent/'affected.json').read_text())]
FACES = [freetype.Face(str(p)) for p in (SOURCE,CLEAN)]
FLAGS = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_AUTOHINT

def bitmap(face, cp, size):
    face.set_pixel_sizes(0,size)
    face.load_char(chr(cp),FLAGS)
    slot=face.glyph
    b=slot.bitmap
    image=Image.frombytes('L',(b.width,b.rows),bytes(b.buffer),'raw','L',b.pitch)
    return image,(slot.bitmap_left,-slot.bitmap_top,slot.bitmap_left+b.width,-slot.bitmap_top+b.rows)

records=[]
atlas=Image.new('RGB',(6*180,math.ceil(len(CP)/6)*100),'white')
labels=ImageDraw.Draw(atlas)
for idx,cp in enumerate(CP):
    for size in (12,14,16,24,28,32):
        (a,ra),(b,rb)=[bitmap(face,cp,size) for face in FACES]
        box=(min(ra[0],rb[0]),min(ra[1],rb[1]),max(ra[2],rb[2]),max(ra[3],rb[3]))
        ca=Image.new('L',(box[2]-box[0],box[3]-box[1]));cb=ca.copy()
        ca.paste(a,(ra[0]-box[0],ra[1]-box[1]));cb.paste(b,(rb[0]-box[0],rb[1]-box[1]))
        difference=ImageChops.difference(ca,cb)
        hist=difference.histogram();total=sum(v*n for v,n in enumerate(hist))
        ink_a=sum(v*n for v,n in enumerate(ca.histogram()));ink_b=sum(v*n for v,n in enumerate(cb.histogram()))
        records.append(dict(codepoint=f'U+{cp:04X}',ppem=size,before_bbox=ra,after_bbox=rb,
                            before_ink=ink_a,after_ink=ink_b,changed_pixels=sum(hist[1:]),
                            difference_over_before_ink=total/ink_a if ink_a else None))
        if size==28:
            x,y=(idx%6)*180,(idx//6)*100
            labels.text((x+4,y+2),f'U+{cp:04X} before / clean',fill='black')
            atlas.paste(ImageChops.invert(ca).convert('RGB'),(x+8,y+23))
            atlas.paste(ImageChops.invert(cb).convert('RGB'),(x+92,y+23))
atlas.save(HERE/'cleanup-raster-28.png')
report=dict(renderer='FreeType; FT_LOAD_NO_HINTING | FT_LOAD_NO_AUTOHINT | FT_LOAD_RENDER',
            sizes=[12,14,16,24,28,32],rows=records,
            max_difference_over_before_ink=max(r['difference_over_before_ink'] for r in records),
            bitmap_bbox_changes=sum(r['before_bbox']!=r['after_bbox'] for r in records))
(HERE/'cleanup-raster-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
