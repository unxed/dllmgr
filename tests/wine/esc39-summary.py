#!/usr/bin/env python3
"""#39: summarise esc39-run.sh results.txt as a Markdown table per image."""
import re
import statistics
import sys
from collections import defaultdict

rows = defaultdict(list)
for line in open(sys.argv[1]):
    name, rest = line.split(' ', 1)
    if name == 'warmup':
        continue
    image = name.split('-')[0]
    f = dict(re.findall(r'(\w+)=(\S+)', rest))
    rows[(image, int(f['delay_ms']))].append(f)


def med(values):
    values = [int(v) for v in values if int(v) >= 0]
    return str(int(statistics.median(values))) if values else '-'


print('| image | Esc at ms | outcomes | handled at ms (median) | image visible ms | TForm ms | TFullScreenWindow ms | foreground at Esc |')
print('|---|---|---|---|---|---|---|---|')
for (image, delay) in sorted(rows, key=lambda k: (['small', 'big', 'none'].index(k[0]) if k[0] in ('small', 'big', 'none') else 9, k[1])):
    fs = rows[(image, delay)]
    outcomes = ' '.join(f['outcome'] for f in fs)
    handled = med(f['exit_ms'] if f['outcome'] == 'exit' else f['confirm_ms'] for f in fs)
    fg = ' '.join(sorted({re.sub(r'^[0-9A-Fa-f]+:', '', f['fg_at_esc']) for f in fs}))
    print(f"| {image} | {'observe' if delay < 0 else delay} | {outcomes} | {handled} | "
          f"{med(f['first_image_ms'] for f in fs)} | {med(f['tform_visible_ms'] for f in fs)} | "
          f"{med(f['fullscreen_visible_ms'] for f in fs)} | {fg} |")
