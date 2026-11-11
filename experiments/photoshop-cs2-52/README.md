# #52 text on the private runtime

Probe: tests/wine/text-aa.sh (tests/wine/text-aa.c), stand :95, 192 DPI,
non-DPI-aware window, 8 pt fonts (11 px at 96 DPI), four qualities each.

- runtime-exact-2x.png: private runtime v8 (dllmgr-46 exact 2x blocks).
- stock-halftone.png: stock Wine 11.0 (halftone stretch).

Findings (2026-11-09):
1. Neither shows any antialiasing, for any quality, including
   ANTIALIASED_QUALITY and CLEARTYPE_QUALITY. WINEDEBUG=+font:
   `freetype_get_aa_flags font L"Tahoma" -11 aa disabled by GASP` (also MS
   Shell Dlg, Arial, Courier New -> Liberation). The fonts' gasp tables ask
   for no gray at this size and Wine honours that for every smoothing mode;
   ClearType quality is turned into grayscale (subpixel path not taken here)
   and then into bitmap by gasp.
2. So the glyphs are identical; stock looks soft only because halftone
   blurs the 96-DPI bitmap, the runtime shows the same bitmap as sharp 2x2
   blocks ("contrasty but badly shaped", owner). The letter shapes (glued
   "pt", heavy "a", gaps) are 11-px hinted bitmaps; scaling cannot fix them.
3. Windows default is ClearType, which smooths horizontally at all sizes
   (gasp DOGRAY only governs standard grayscale smoothing).

Options: (a) Windows-like ClearType in the runtime: do not let gasp
switch ClearType text to bitmaps, and turn ClearType on in the recipe
(interim: smooth edges, same 11-px shapes); (b) the real fix: render text
at the physical DPI inside the scaled surface, like Windows "GDI scaling"
for non-DPI-aware GDI apps (true 22-px glyph shapes); (c) exact/halftone as
a setting.

## dllmgr-52 (2026-11-09): selectable text smoothing

Owner: start with (a) and let the user choose. patches/dllmgr-52.patch
(win32u font.c/freetype.c): DLLMGR52_TEXT=system|bitmap|gray|light|cleartype
overrides the per-face fontconfig flags (Windows-like: one system setting),
smooths at every size (gasp "no gray" ignored, as ClearType does on
Windows), `light` uses light hinting; DLLMGR52_GAMMA darkens partial
coverage (smoothed text at 11 px came out washed out). dllmgr-46 got
DLLMGR46_SMOOTH (halftone instead of exact blocks).

modes.png rows: bitmap (v8 today), light 1.6, light 2.2, gray 1.6, gray 2.2,
cleartype. modes-zoom.png (3x, nearest): bitmap, light 2.2, gray 2.2,
cleartype. ClearType at 96 DPI doubled 2x shows colour fringes; gray 2.2 is
the most contrasty and keeps letters apart ("pt", "Sharp"); light 2.2 is
softer with the most faithful shapes.

User choice: `dllmgr set photoshop-cs2 text=gray|light|cleartype|bitmap|system
contrast=1.0..4.0 scaling=exact|smooth`, shown by `dllmgr status`, applied by
`dllmgr run` (and so by the trampoline). Photoshop default: text=gray
contrast=2.2 scaling=exact. FastStone keeps stock text by default.

Photoshop CS2 on the stand (local runtime with dllmgr-52), Edit menu:
photoshop-edit-menu-bitmap-vs-gray.png, left text=bitmap (v8 today), right
text=gray contrast=2.2 (new default). Menu bar and menu items are smoothed.

## To do (owner, 2026-11-11): Courier New and "100%" digits

On runtime-exact-2x.png and stock-halftone.png the Courier New line is
proportional, and "100%" in Arial and Courier New has overlapping zeros
(stock Wine the same). Task: run tests/wine/text-aa on v23 and on rt-gdi with
WINEDEBUG=+font to see which file is really used for Arial and Courier New
(substitution?) and where the digit widths come from; run the same probe on
Windows in CI; write the result here; open a ticket if it reproduces. Not
started (session paused).
