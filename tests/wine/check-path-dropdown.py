"""Check real-app combo behavior and button pixels, independently of theme colors."""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageChops

parser = argparse.ArgumentParser()
parser.add_argument('folder', type=Path)
parser.add_argument('--expect-release-change', action='store_true', help='require the known stock-Wine themed failure')
args = parser.parse_args()
text = (args.folder / 'observations.txt').read_text()
stages = ['00-initial', '01-hover', '02-down', '03-held', '04-up', '05-second-down', '06-second-up', '07-escape']
expected = [(0,0,0),(0,0,0),(1,8,1),(1,8,1),(1,0,1),(0,0,0),(0,0,0),(0,0,0)]
images = {}
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
    image = Image.open(args.folder / f'{stage}.bmp').convert('RGB')
    if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
        raise SystemExit(f'{stage}: button outside capture')
    images[stage] = image.crop(box)

def changes(a,b):
    if images[a].size != images[b].size:
        raise SystemExit('Button geometry changed during click')
    return sum(pixel != (0,0,0) for pixel in ImageChops.difference(images[a],images[b]).getdata())

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
