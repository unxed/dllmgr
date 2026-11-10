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

## How Photoshop draws them (2026-11-10, local debug build)

debug-exttextout-dump.patch (local only, never in a runtime): every
ExtTextOut logs text, font and dx (DLLMGR66_DUMP=1). dump-history-layers.txt:

    "Open"       Tahoma h=-10 weight 700 (bold)          no dx
    "Background" Tahoma h=-10 weight 400 italic          no dx
    "t46.png"    Tahoma h=-10 weight 400                 no dx

So ADM uses real GDI fonts (10 px, ANTIALIASED_QUALITY per the font trace)
and lets GDI place the glyphs; no double strike, no own spacing. The uneven
spacing ("Op en") therefore comes from Wine's Tahoma Bold / synthetic italic
at 10 px themselves (glyph advances and hinting), not from Photoshop.
Next: tests/wine/text-kern66.c renders exactly these fonts in each text mode
to confirm and compare with Windows.

## Cause of the bad spacing (2026-11-10)

tests/wine/text-kern66.c draws exactly Photoshop's fonts (Tahoma -10 bold,
-10 italic, ANTIALIASED_QUALITY) and shows the same "Op en" / "B ackground"
(probe-tahoma10-system-vs-gray.png, left text=system, right text=gray).

Wine's own tahomabd.ttf contains embedded bitmap strikes for 9, 10, 11, 12,
13, 15, 16 px. At 10 px the bitmaps are badly spaced (left bearing / width /
right bearing in pixels, from FreeType):

    strike 10 px:      O 1/7/0   p 0/5/2   e 0/5/1   n 0/5/2   B 0/6/2
    outline, unhinted: O 0.23/7.23/0.23   p 0.55/5.59/0.16   e 0.14/5.59/0.20   B 0.67/5.73/0.45

The outline puts p a little right of its cell (0.55 px left, 0.16 px right);
the bitmap puts it hard left with 2 px on the right: "O" and "p" touch and a
gap opens before "e". Same for B (0/6/2). In mono rendering (stock text, what
system Wine shows) Wine uses these bitmaps; with text=gray the outline is used
and the spacing is better but the strokes heavier.
So the kerning is a defect of Wine's Tahoma Bold bitmap strikes, not of
Photoshop or of our scaling.

## Fix (2026-11-10, patches/dllmgr-66.patch, win32u freetype.c)

Monochrome glyphs of Wine's Tahoma (family "Tahoma" with embedded strikes)
are rendered from the hinted outlines instead of the strikes
(DLLMGR66_TAHOMA_BITMAPS=1 keeps the strikes). Probe at 96 DPI
(probe-tahoma10-before-after.png, left stock, right fixed): "Open",
"Background" evenly spaced and crisp. Offline FreeType rendering of 10/11 px
strikes vs hinted outlines: /home/claude/work/tfix (variants.png).

Narrowed (2026-11-10): only the bold face skips its strikes. FreeType count
of printable ASCII glyphs shifted >= 1 px against the outline side bearings:
tahomabd 9/10/11/12/13/15/16 px = 4/16/19/20/51/53/53 of 94; tahoma (regular)
1-4 of 94 per size, so its designed strikes stay. WineHQ text:
docs/bugzilla/dllmgr-66.txt (outbox 10).

Photoshop on the stand with the bold-only fix (photoshop-before-after-bold-fix.png):
1 stock text before, 2 stock text after ("Op en" -> "Open"), 3 ours (gray) before,
4 ours after. In gray mode "Background" (synthetic italic of the regular face)
stays heavy: smoothing + contrast curve, a separate question from spacing.

## Windows reference (2026-11-10, text-probe-windows.yml run 42732000312)

tests/wine/text-kern66.c renders Photoshop's palette fonts into a 96-DPI
DIB (no screen grab), rows: bold 10/11 px, italic 10/11 px, regular 10/11 px.
windows-vs-wine-palette-fonts.png, panels top to bottom: Windows Server 2025
GDI (MS Tahoma), Wine 11.0 stock, Wine + dllmgr-66 (text=system), Wine +
dllmgr-66 with text=gray contrast=2.2.

- Bold 10 px: Windows compact and even. Stock Wine strikes: "Op en",
  "B ackground". dllmgr-66 (hinted outlines): even, but about 13 % wider than
  Windows (and than the strikes): outline advances are larger.
- Italic (synthetic, Tahoma has no italic): Windows draws it crisp black (no
  smoothing at this size); Wine draws it smoothed, grey and faint.
- Regular: close to Windows in stock/system mode; text=gray squeezes 10 px.

So the better fix for bold is to keep the strikes' widths (close to Windows)
and correct where each bitmap sits in its cell; and synthetic italic should
follow the same no-smoothing rule as the upright face.

## Per-glyph comparison with Windows (2026-11-10)

tests/wine/text-metrics66.c writes the monochrome GDI metrics (left, black
box width, advance) of Tahoma regular / bold / simulated italic at 9-16 px;
metrics/windows.csv (text-probe-windows.yml), metrics/wine-stock.csv,
metrics/wine-dllmgr66-v4.csv. Findings:
- Wine's regular Tahoma strikes have exactly Windows' advances at every
  strike size (14 px has no strike: 31 of 94 differ).
- The Bold strikes do not (10 px: 40 of 94 advances differ, p/n 7 vs 6, B 8
  vs 7). Hinted outlines (fix v1) were the worst (10 px: 62, text 8 % wider).
- Wine's simulated italic is wider than Windows', whose italic advances
  equal the upright ones; Windows draws it unsmoothed by shifting the rows of
  the upright bitmap.

patches/dllmgr-66.patch (v4):
- Tahoma Bold keeps its strikes, each glyph gets its outline advance rounded
  to whole pixels. Advance mismatches vs Windows 9..16 px: 47 24 13 15 36 6 5 5
  (strikes: 48 40 24 28 46 42 21 21).
- Simulated italic of Tahoma: the upright glyph's advance (0 mismatches at all
  strike sizes) and, for monochrome glyphs at strike sizes with no other
  transform, the upright strike with its rows shifted by
  round((height above baseline + 0.5) * 0.34), the best fit to Windows' black
  boxes (DLLMGR66_OUTLINE_ITALIC=1: Wine's sheared outline).
- gasp also decides for simulated bold/italic, as on Windows: italic at 10-11
  px crisp, not grey (DLLMGR66_AA_FAKES=1: Wine's default).
Images: windows-vs-wine-v4.png (Windows / v3 / v4),
italic-windows-vs-v4-zoom.png (Windows 10/11 px, Wine v4 10/11 px),
photoshop-stock-v3-v4.png (Photoshop at 2x: stock, v3, v4).
