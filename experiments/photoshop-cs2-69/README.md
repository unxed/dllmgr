# #69 stem phase: uneven stems with fractional positioning (Photoshop CS2)

Owner, 2026-11-10: in Photoshop CS2 (Tahoma 10-11 px, 192 DPI, DLLMGR52_TEXT=agg-rgb)
"tr" in "Contrast:" (Brightness/Contrast dialog) looks heavier than the other letters.
Task: treat it as a continuation of Shemanarev's "Texts Rasterization Exposures":
reduce stem-phase unevenness **without giving up fractional positioning**, apply it,
verify it.

Result: **soft stem snapping with a run-level phase choice** (`stem-fix.diff`,
opt-in `DLLMGR69_STEM=1`). In the Photoshop dialog the "Contrast:" stems go from
0.40 / 0.40 / 1.00 / 0.70 / 0.70 / 1.00 (n n t r a t, darkness) to 1.00 for all six; on
the lab's 32 words, stem-darkness CV halves (agg-rgb 0.121 -> 0.059) while the
white between letters stays as designed (RMS error 0.155 -> 0.163 px, centroid
spacing 0.130 -> 0.125 px). Hard snapping (what hinting does) gets 0.022, but it
doubles the spacing error (0.357 px).

## 1. The problem, measured

Shemanarev hints vertically only and places glyphs at fractional x (we use 1/3 px
phases). The cost, which his article accepts: a ~1 px vertical stem lands either on
one pixel column (dark, crisp) or across two (half as dark on each, blurred),
depending on where the glyph's fractional position puts it. Along a word the stems'
weight therefore "walks".

**Stem darkness by where the stem's left edge falls in the pixel** (all straight
stems of the lab's glyphs, Tahoma regular, every phase; median peak darkness (sRGB,
1 = black) / ink per row (linear, px); `scripts/phase_table.py`,
`data/phase_table.txt`):

| size | mode | variant | edge 0 | 1/6 | 2/6 | 3/6 | 4/6 | 5/6 | peak range |
|---|---|---|---|---|---|---|---|---|---|
| 10 | agg-rgb | current | 0.68 | 0.66 | 0.54 | **0.50** | 0.57 | 0.64 | 0.18 |
| 10 | agg-rgb | stem fix | 0.68 | 0.69 | 0.62 | 0.62 | 0.64 | 0.68 | 0.07 |
| 11 | agg-rgb | current | 0.71 | 0.68 | 0.53 | **0.51** | 0.66 | 0.69 | 0.20 |
| 11 | agg-rgb | stem fix | 0.73 | 0.71 | 0.65 | 0.63 | 0.70 | 0.71 | 0.09 |
| 10 | agg (grey) | current | 1.00 | 0.70 | 0.59 | **0.51** | 0.51 | 0.59 | 0.49 |
| 10 | agg (grey) | stem fix | 1.00 | 0.92 | 0.70 | 0.70 | 0.70 | 0.70 | 0.30 |
| 11 | agg (grey) | current | 1.00 | 0.70 | 0.51 | **0.51** | 0.59 | 0.70 | 0.49 |
| 11 | agg (grey) | stem fix | 1.00 | 1.00 | 0.70 | 0.70 | 0.70 | 1.00 | 0.30 |

A stem centred on a pixel boundary loses 30 % (rgb) to 50 % (grey) of its peak
darkness; ink per row is nearly constant (the blur spreads it, does not lose it).

**"Contrast:" at Photoshop's placement** (stem@left-edge phase: peak;
`data/contrast_word.txt`), 11 px agg-rgb: n 0.67, n **0.49**, t 0.66, r 0.67, a 0.54,
t 0.66; grey: n 0.59, n **0.51**, t **0.70**, r 0.59, a 0.51, t **0.70**.

**In Photoshop itself** (stand, `probe/ps-stand.sh`, `scripts/shot_stems.py`,
`data/photoshop-dialog-strokes.txt`): the Brightness/Contrast dialog draws its
labels in **grey** AA (not subpixel, even with agg-rgb; see findings), ~11 px,
upscaled 2x as exact blocks. "Contrast:" stem darkness in the X frame: n 0.40, n
0.40, t 1.00, r 0.70, a 0.70, t 1.00: the t's are the only crisp black stems, which
is what the owner sees as heavy "t...r...t".

Bold: Wine's Tahoma Bold at 10/11 px uses bitmap strikes (dllmgr-66), so it has no
stem phase; the probe confirms the stem fix leaves bold lines byte-identical.

## 2. Candidates evaluated

Lab: `scripts/ftlab.py` (Wine's agg pipeline on the same FreeType, Shemanarev's LCD
filter, Wine's grey ramp), `scripts/measure.py` (variants and metrics), 32 words
(20 English, 12 Russian Photoshop UI words), Tahoma regular 10 + 11 px.
Metrics: CV of stem peak darkness at 1x, after the owner's panel (2x exact
blocks, then scripts/as-seen.py's 1/1.6 bilinear, averaged over sampling phases),
and with Wine's halftone 2x (scaling=smooth); CV of stem ink; RMS error of the white
gap between neighbours vs the exact outline at its exact fractional position; RMS /
max error of neighbour distance (coverage centroids); |run ink extent - ideal|.
`scripts/candidates.py`, `data/candidates-10-11.txt`:

| mode | id | candidate | peak cv | seen | smooth | ink cv | white rms | centroid rms / max | width |
|---|---|---|---|---|---|---|---|---|---|
| rgb | A | agg (current): 1/3 px phases, vertical-only hinting | 0.121 | 0.119 | 0.123 | 0.100 | 0.155 | 0.130 / 0.30 | 0.60 |
| rgb | B | whole-px positions + full hinting (classic) | 0.013 | 0.042 | 0.108 | 0.094 | 0.562 | 0.517 / 1.61 | 0.82 |
| rgb | C | finer phases: 1/6 px | 0.129 | 0.126 | 0.126 | 0.095 | 0.092 | 0.071 / 0.19 | 0.62 |
| rgb | D1 | global darkening: embolden 0.2 px | 0.110 | 0.109 | 0.109 | 0.082 | 0.251 | 0.130 / 0.34 | 0.94 |
| rgb | D2 | phase-dependent darkening k=1 | 0.123 | 0.118 | 0.129 | 0.109 | 0.210 | 0.130 / 0.31 | 0.69 |
| rgb | D3 | phase-dependent darkening k=2 | 0.147 | 0.140 | 0.155 | 0.126 | 0.278 | 0.131 / 0.32 | 0.69 |
| rgb | E | per-glyph phase for the sharpest bitmap (Viterbi, +-1/3 px) | 0.121 | 0.119 | 0.123 | 0.100 | 0.155 | 0.130 / 0.30 | 0.60 |
| rgb | F1 | hard stem snap to whole px (outline warp), advance fractional | 0.022 | 0.047 | 0.109 | 0.061 | 0.357 | 0.331 / 0.88 | 0.65 |
| rgb | F2 | hard stem snap to a 1/3 px grid | 0.102 | 0.103 | 0.112 | 0.103 | 0.184 | 0.160 / 0.42 | 0.60 |
| rgb | G | F1 + rounding/phase chosen by Viterbi on white gaps | 0.022 | 0.047 | 0.109 | 0.062 | 0.270 | 0.246 / 0.77 | 0.71 |
| rgb | H | soft stem snap 0.5 + Viterbi (float model) | 0.054 | 0.066 | 0.113 | 0.063 | 0.163 | 0.127 / 0.41 | 0.71 |
| rgb | **I** | **chosen: soft snap 128/256 + phase Viterbi (C, stem-fix.diff)** | **0.059** | **0.069** | 0.116 | 0.067 | **0.163** | **0.125** / 0.42 | 0.66 |
| rgb | I192 | as I, alpha 192/256 (DLLMGR69_STEM=192) | 0.040 | 0.057 | 0.113 | 0.066 | 0.245 | 0.179 / 0.67 | 0.65 |
| grey | A | agg (current) | 0.295 | 0.287 | 0.265 | 0.109 | 0.155 | 0.131 / 0.33 | 0.37 |
| grey | B | whole px + full hinting | 0.027 | 0.054 | 0.139 | 0.083 | 0.562 | 0.521 / 1.62 | 0.92 |
| grey | C | 1/6 px | 0.286 | 0.281 | 0.258 | 0.101 | 0.092 | 0.072 / 0.20 | 0.37 |
| grey | D1 | embolden 0.2 px, gamma 1.4 | 0.326 | 0.324 | 0.308 | 0.077 | 0.251 | 0.132 / 0.33 | 0.37 |
| grey | D3 | phase-dependent darkening k=2 | 0.222 | 0.206 | 0.209 | 0.177 | 0.278 | 0.155 / 0.41 | 0.37 |
| grey | E | sharpest phase | 0.238 | 0.236 | 0.244 | 0.119 | 0.271 | 0.251 / 0.78 | 0.67 |
| grey | F1 | hard snap whole px | 0.000 | 0.051 | 0.136 | 0.123 | 0.357 | 0.331 / 0.88 | 0.96 |
| grey | G | hard snap + Viterbi | 0.000 | 0.051 | 0.136 | 0.122 | 0.270 | 0.246 / 0.78 | 0.87 |
| grey | **I** | **chosen (alpha 128)** | **0.192** | 0.193 | 0.212 | 0.104 | **0.163** | 0.129 / 0.43 | 0.48 |
| grey | I192 | alpha 192 | 0.130 | 0.140 | 0.186 | 0.097 | 0.245 | 0.185 / 0.70 | 0.53 |

What each line teaches:

- **C (finer phases)** fixes spacing (white 0.092) but not stems: the unevenness comes
  from where a stem sits in the pixel, not from coarse quantisation.
- **D (darkening)**, global or by phase, adds ink where stems are blurred but cannot
  un-blur them; it raises ink variance and white-gap error. Rejected.
- **E (choose the sharpest of the neighbouring thirds)**: a 1/3 px move rarely brings a
  stem onto the grid; in rgb the spacing penalty always wins (= A), in grey it costs
  spacing for little. Rejected.
- **F2 (1/3 px stem grid)**: in rgb a 1/3-aligned 1 px stem still straddles two
  pixel columns after the 5-tap filter. No gain.
- **F1 / G / B (hard snapping)**: perfect stems, but every stem moves up to 0.5 px
  and the white between letters walks instead (2-3.5x the error). This is exactly
  the trade-off Shemanarev describes for hinting. Rejected.
- **H / I (soft snapping)**: each straight stem moves *half way* to its snapped place
  (keeping its width, so its ink); the outline is warped piecewise linearly between
  stem edges, the advance stays fractional. A Viterbi pass over the run then picks,
  per glyph, its third or the one left/right, so the white between neighbours
  (counting where the warp moved the first/last stem edge) stays as designed: the
  remainder of each snap is "diffused" into the choice of phases, optimally over the
  run instead of greedily. Half the unevenness gone, spacing unchanged.

Alpha sweep (`data/alpha-sweep-10-11.txt`, rgb): peak cv 0.121 / 0.088 / 0.072 /
**0.059** / 0.049 / 0.040 / 0.035 for alpha 0 / 64 / 96 / **128** / 160 / 192 / 256,
white-gap RMS 0.155 / 0.141 / 0.148 / **0.163** / 0.198 / 0.245 / 0.266. 128 is the knee:
beyond it spacing degrades quickly. (Alpha 64 even improves spacing, because the
phase choice also absorbs part of the 1/3 px quantisation.)

Stem detector (`data/detectors-rgb.txt`): the first C version (wip, commit
0ea85b1) treated every tall column group as a stem, so it also warped round bowls
(o, c, e, s sides) and slivers: white-gap RMS 0.196-0.209. The final one keeps only
**straight** stems (in at least ~half an x-height of rows the ink run through the
group's middle column starts and ends within 1/8 px of the group's edges):
0.163, with the same stem gain.

Larger sizes, same metrics (`data/candidates-13-16.txt`, `-20-22-native2x.txt`):
13/16 px rgb peak cv 0.092 -> 0.053, white 0.132 -> 0.129; 20/22 px (#52b native 2x)
rgb 0.058 -> 0.043, white 0.134 -> 0.136. The gain shrinks with size (stems get
wider than the blur) and costs nothing in spacing. Under Wine's halftone 2x
(scaling=smooth) the gain mostly disappears (0.123 -> 0.116): the halftone blur
dominates.

## 3. The chosen fix (stem-fix.diff)

`stem-fix.diff`: a/ b/ diff against /home/claude/work/wine-11.0 (dlls/win32u/freetype.c,
dlls/win32u/dibdrv/graphics.c, dlls/win32u/ntgdi_private.h), on top of dllmgr-69.
Off by default; `DLLMGR69_STEM=1` (alpha 128), `DLLMGR69_STEM=2..256` (that alpha
/256), only with DLLMGR52_TEXT=agg or agg-rgb, outline glyphs without transforms.

- freetype.c, `get_glyph_outline` for an agg glyph at phase p: find the straight
  stems (outline rasterised 16x wide, as above; at most 8, else none), move each
  alpha/256 of the way to its snapped place (width rounded to whole px, >= 1, left
  edge on a pixel edge), keep its width; skip the glyph when a stem would move more
  than 0.75 px or stems would collide; warp the outline piecewise linearly (constant
  shift outside the stems). A metrics-only query (`DLLMGR69_STEMQ`) returns the
  displacement of the first and last stem edge.
- dibdrv/graphics.c, `agg_place_run`: per glyph three options (its third, one
  less, one more); Viterbi minimises 20 * (left-edge error_i - right-edge
  error_{i-1})^2 + (mean edge error_i)^2; the first and last glyph may take a
  shifted third only with both edge errors within 0.5 px. `render_agg_run` then
  draws at the chosen thirds; all else is unchanged.
- Glyph cache: the stem-warped bitmaps are cached per phase like the plain ones.

Bit-exact model: `scripts/cmodel.py` (+ `scripts/straight.py`); C harnesses
`scripts/ctest/` (helpers.inc and place.c are extracted from the patched tree).

## 4. Verification

- Builds without warnings (`make dlls/win32u/win32u.so`, wine-build64), installed in
  rt-cur3.
- C vs model: 1416/1416 glyph renders identical (knots and every warped point;
  regular+bold, 10/11 px, alpha 128/192, 3 phases, all lab characters;
  `scripts/crosscheck.py`), 256/256 runs placed identically (`crosscheck_place.py`).
- Wine vs model: `probe/stem-words.c` (the 32 words, Tahoma -10/-11 regular/bold,
  DEFAULT_QUALITY, 96-DPI DIB) on rt-cur3: agg-rgb regular lines **64/64 bit-identical**
  to the model, with the fix and without (`scripts/wvm4.py`,
  `data/wine-vs-model-rgb.txt`); every line differs between the two.
- Off path: without DLLMGR69_STEM the patched win32u.so renders the probe
  byte-identical to the original rt-cur3 win32u.so (agg and agg-rgb, md5).
- Bold lines (bitmap strikes): byte-identical with and without the fix.
- Photoshop CS2 on the stand (:95, Muffin, prefix-auto, rt-cur3, agg-rgb), Image >
  Adjustments > Brightness/Contrast (`images/ps-*`):

  | "Contrast:" stem | n | n | t | r | a | t |
  |---|---|---|---|---|---|---|
  | current (X frame) | 0.40 | 0.40 | 1.00 | 0.70 | 0.70 | 1.00 |
  | DLLMGR69_STEM=1 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

  As seen on the owner's 125 % panel (as-seen.py on the full frame): Contrast: stroke
  peaks min/max 0.40/0.91 -> 0.49/0.93, Brightness: 0.40/1.00 -> 0.53/1.00
  (strokes found by a simple column detector, bowls included; see the script).

Images: `images/ps-dialog-frame-before-after.png` (dialog, top current, bottom
fix), `images/ps-dialog-seen-x4-before-after.png` (owner's panel, x4),
`images/ps-contrast-frame-x8-before-after.png`, `images/probe-agg-rgb-{1x,seen}.png`
and `images/probe-agg-{1x,seen}.png` (probe words, current / fix, 11 and 10 px).

## 5. Findings outside this task (not acted on)

1. Photoshop's Brightness/Contrast dialog labels are grey AA, not subpixel, with
   DLLMGR52_TEXT=agg-rgb (font.c: a preset `aa_flags` takes the DLLMGR52_SYSTEM
   branch; cause not checked). So the owner's complaint is in fact the grey mode.
2. The lab's grey output model (`ftlab.to_pixels`) is not bit-exact against Wine's
   grey agg in the 96-DPI DIB probe (Wine's darkest level there is 0x4d, never black;
   Photoshop's dialog does show black). The grey numbers in section 2 are model
   numbers; the rgb ones are verified bit-exact. The Photoshop measurements are real.
3. With scaling=smooth (halftone 2x) the stem gain largely vanishes (section 2).

## Files

- `stem-fix.diff`: the patch (diff -ru a/ b/, applies with `patch -p1` in wine-11.0).
- `scripts/`: ftlab.py, measure.py, stems.py, straight.py, cmodel.py (lab, metrics,
  model of the C), candidates.py, sweep_alpha.py, sweep_c3.py, phase_table.py,
  contrast_word.py, crosscheck*.py + ctest/ (C vs model), wine_vs_model.py / wvm*.py
  (Wine vs model), shot_stems.py (screenshots), probe_images.py, older table*.py,
  pareto.py, sheet*.py (exploration by the previous agent). Python needs freetype-py
  (`PYTHONPATH` to a freetype-py checkout) and numpy/Pillow.
- `probe/`: stem-words.c (+ runprobe.sh), ps-stand.sh (Photoshop on the stand).
- `data/`: all tables quoted above.
