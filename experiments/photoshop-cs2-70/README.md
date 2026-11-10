# #70 Type tool cursor appears late on first use

Owner, 2026-11-10 (runtime v13/v14, text=agg-rgb): selecting the Type tool
for the first time, the cursor over the canvas changes only after a few
seconds.

Facts on the stand (fresh CS2 trial reinstall, rt-cur3 = v14 code):
- Over the canvas Photoshop hides the X cursor (curwatch.c: a 64x64 empty
  X cursor) and draws the tool cursor into the window itself.
- first-type.sh: fresh start, document open, one click on the Type tool,
  canvas sampled every 0.25 s. text=gray, 335 system fonts: I-beam after
  ~0.6 s; 701 fonts (fonts-indic + fonts-noto-core, as in the owner's log):
  ~0.6 s. Not reproduced so far.
- Hypothesis under test: the first Type tool selection builds the font
  list of the options bar; on the owner's machine with many more fonts (and
  AGG glyph caching) that could take seconds. Next: text=agg-rgb, then the
  owner's font count (fc-list | wc -l).
