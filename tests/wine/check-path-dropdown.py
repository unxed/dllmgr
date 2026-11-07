"""Check real-app combo behavior and button pixels, independently of theme colors."""
import argparse
import json
import re
from pathlib import Path
import struct

parser = argparse.ArgumentParser()
parser.add_argument('folder', type=Path)
parser.add_argument('--expect-release-change', action='store_true', help='require the known stock-Wine themed failure')
args = parser.parse_args()
text = (args.folder / 'observations.txt').read_text()
stages = ['00-initial', '01-hover', '02-down', '03-held', '04-up', '05-second-down', '06-second-up', '07-escape']
expected = [(0,0,0),(0,0,0),(1,8,1),(1,8,1),(1,0,1),(0,0,0),(0,0,0),(0,0,0)]
images = {}

def button_pixels(path, box):
    data = path.read_bytes()
    if data[:2] != b'BM' or len(data) < 54:
        raise SystemExit('Invalid capture BMP')
    offset = struct.unpack_from('<I', data, 10)[0]
    header_size,width,height,planes,bits,compression = struct.unpack_from('<IiiHHI', data, 14)
    if header_size != 40 or width <= 0 or height >= 0 or planes != 1 or bits != 32 or compression != 0:
        raise SystemExit('Expected probe top-down 32-bit uncompressed BMP')
    height = -height
    if len(data) < offset + width*height*4:
        raise SystemExit('Truncated capture')
    left,top,right,bottom = box
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise SystemExit('Button outside capture')
    # Ignore unused alpha; compare all BGR pixels in the public button rectangle.
    return (right-left,bottom-top), [data[offset+(y*width+x)*4:offset+(y*width+x)*4+3]
                                   for y in range(top,bottom) for x in range(left,right)]

for stage, (dropped,pressed,visible) in zip(stages, expected):
    pattern = (rf'^stage={stage} dropped=(\d+) button_state=(\d+) .* list_visible=(\d+) '
               r'combo_rect=([\d,-]+) button=([\d,-]+)$')
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise SystemExit(f'{stage}: missing public state/geometry')
    actual = tuple(map(int, match.group(1,2,3)))
    if actual != (dropped,pressed,visible):
        raise SystemExit(f'{stage}: state {actual}, expected {(dropped,pressed,visible)}')
    box = tuple(map(int, match.group(5).split(',')))
    images[stage] = button_pixels(args.folder / f'{stage}.bmp', box)

def changes(a,b):
    if images[a][0] != images[b][0]:
        raise SystemExit('Button geometry changed during click')
    return sum(x != y for x,y in zip(images[a][1],images[b][1]))

result = {'hover_to_down_pixels': changes('01-hover','02-down'),
          'down_to_held_pixels': changes('02-down','03-held'),
          'down_to_up_pixels': changes('02-down','04-up')}
(args.folder / 'pixel-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
if result['hover_to_down_pixels'] == 0 or result['down_to_held_pixels'] != 0:
    raise SystemExit('Pressed state missing or unstable while held')
if args.expect_release_change:
    if result['down_to_up_pixels'] == 0:
        raise SystemExit('Expected the known stock release-paint change')
else:
    if result['down_to_up_pixels'] != 0:
        raise SystemExit('Button painting changed after release while the dropdown stayed open')
