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
