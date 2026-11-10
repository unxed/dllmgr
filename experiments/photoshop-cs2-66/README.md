# #66 palette text (History "Open" bold, Layers "Background" italic)

Stand, 192 DPI, rt-cur3 (v11 code), C:\t46.png open, one setting per run
(stand-palettes-4-modes.png, zoom stand-palette-text-4-modes.png), left to right:
1. stock text + halftone scaling (DLLMGR46_SMOOTH=1, no DLLMGR52_TEXT): what
   system Wine shows; thin 1-bit glyphs, uneven spacing ("Op en").
2. ours (text=gray contrast=2.2 scaling=exact, Photoshop default): even
   spacing, but the smoothed glyphs with the contrast curve make bold and
   italic heavy and smudgy ("Background" looks bold).
3. text=bitmap exact: like 1 but blocky.
4. GDI scaling (opt-in prototype) with gray/2.2: real 22-px glyphs, same
   heaviness as 2.

Font trace: the palette text is GDI Tahoma -11 (thousands of CreateFont),
bold Tahoma created only 4 times, no italic font at all: Photoshop's ADM
draws "Background" italic/bold itself (shear / double strike) over GDI text,
so the smoothing + contrast of every stroke is doubled. Owner (2026-11-10):
the stock look (1) is much better for these. To compare with Windows: CI
capture of the same palettes (tests/wine/ps35-measure.ps1, pending).
