# #52 step (b): text at the physical DPI ("GDI scaling")

Owner, 2026-11-09: wants contrast *and* real letter shapes. Step (a)
(dllmgr-52: smoothing at every size, contrast) is done; it cannot change the
shapes, which are 11-px glyphs doubled. Step (b): a non-DPI-aware window is
drawn directly at the physical resolution, like Windows 10 "GDI scaling"
for GDI applications.

## Today (dllmgr-46)

A non-DPI-aware window gets a `scaled_surface` (win32u/dce.c) at 96 DPI;
the application draws into it, `scaled_surface_flush` stretches the dirty
part into the driver surface at the monitor DPI (exact 2x blocks or
halftone).

## Design

For an integer factor k (192 DPI: k = 2) and opt-in (`dllmgr set APP
scaling=gdi`, env DLLMGR52_GDI_SCALE=1):

1. Window DCs of such a window draw into the target (driver) surface, not
   into the 96-DPI bits: `update_visible_region` passes the target surface,
   the visible region, `win_rect` and `top_rect` multiplied by k.
2. The DC gets a hidden scale k under the application's own mapping:
   world -> viewport transform times k (dc.c, where xformWorld2Vport is
   built). Lines, fills, text positions and font sizes are scaled by the
   transform, so text is rasterised at 22 px with real hinting and shapes.
3. Calls whose sizes are in device pixels must be scaled explicitly:
   SetDIBitsToDevice (becomes StretchDIBits), region arguments in device
   coordinates (ExtSelectClipRgn / SelectClipRgn, GetClipRgn /
   GetRandomRgn results), DPtoLP/LPtoDP stay in the scaled space (as on
   Windows with GDI scaling: the application sees logical units).
4. Bitmaps (BitBlt from memory DCs, icons) are stretched by the transform,
   so they look as today (exact blocks or halftone, same setting).
5. The scaled surface keeps its role for window-level operations (moves,
   scrolling, non-client); its flush must not overwrite pixels the DC drew
   directly: the 96-DPI bits are not written any more, so the flush of a
   GDI-scaled window is skipped, and window-level copies (move_window_bits)
   are done on the target surface in k-scaled rectangles.

## Risks (stale pixels are never acceptable)

- Window moves / scrolls copying 96-DPI bits that are no longer current.
- Applications that read back window pixels (BitBlt from the window DC,
  GetPixel) get downsampled values; Photoshop reads back for the brush
  outline (XOR) and the marquee: verify #46 stays fixed.
- Device-coordinate APIs missed in step 3.

## Stages (each verifiable on the stand, opt-in until the owner accepts)

1. tests/wine/text-aa.exe: window DC hidden scale + target surface; text at
   22 px; screenshot comparison with scaling=exact.
2. Device-coordinate APIs (step 3), then Photoshop: menus, palettes,
   dialogs, the brush outline (#46), marquee, zoom (#47).
3. Window moves / scrolling (step 5), then the owner retest.

## Stage 1 result (2026-11-09)

patches/dllmgr-52-gdi.patch (applies after dllmgr-46 and dllmgr-52; not in
the runtime build yet, opt-in DLLMGR52_GDI_SCALE=1): hidden DC scale in
construct_window_to_viewport, window DCs of an integer-scaled window get the
target surface and k-scaled visible region / rects, the scaled surface is
marked direct (its flush only passes exposures on and flushes the target).

- text-aa.exe: real 22-px glyphs, normal shapes, smoothed
  (experiments/photoshop-cs2-52/gdi-scaling-text-zoom.png: top exact 2x,
  bottom GDI scaling).
- Photoshop: starts, but much is wrong
  (gdi-scaling-photoshop-stage1.png): the canvas is drawn at 1x size into
  the top-left quarter (device-size blits: SetDIBitsToDevice /
  StretchDIBits with pixel sizes), the menu bar and option texts are
  missing, the toolbox is cut. Stage 2 = the device-coordinate APIs.

## Stage 2, first step (2026-11-09)

SetDIBitsToDevice on a scaled DC stretches by k (nulldrv path,
COLORONCOLOR); ExtSelectClipRgn scales the region by k, OffsetClipRgn the
offset, GetRandomRgn reports 96-DPI device coordinates. Photoshop
(gdi-scaling-photoshop-stage2.png): canvas, palettes, toolbox and menu bar
are complete and crisp. Left: combo box texts ("Normal" in Style and
Layers) show only their upper half, the "Style:" label is cut.

### Stage 2 open items (2026-11-09, probe tests/wine/gdi-scale-combo.c)

gdi-scaling-combo-probe.png (left today, right GDI scaling), the same
problems as Photoshop's option bar, now reproducible in 30 lines:
1. Parts of the parent window are never painted (black): its background
   erase covers only the 96-DPI quarter (an erase path that does not go
   through the DC transform; Photoshop's combo clip IntersectClipRect
   2,2,42,8 from comctl32 points the same way).
2. Raster (bitmap) fonts such as System are not scaled: glyphs stay 1x
   while advances double ("N o r m a l"). Needs a vector substitute
   (or integer scaling of raster glyphs) on GDI-scaled DCs.
3. A combo box with Tahoma draws fine, with an extra frame line below it
   (also an erase/region issue).
Photoshop trace (relay, 30 s of start): SelectClipRgn 9442,
SetWindowOrgEx 4060, SetViewportOrgEx/OffsetViewportOrgEx 331 each,
IntersectClipRect 189, DrawTextW 129, StretchDIBits 50, GetClipBox 46.

### Stage 2, second step (2026-11-09)

- LPtoDP / DPtoLP hide the scale (the application keeps seeing 96-DPI
  device units, as with Windows GDI scaling). Cause of the unpainted
  areas: user32/comctl32 set_control_clipping treats the client rectangle
  as device coordinates and converts it with DPtoLP.
- Raster fonts are not used on GDI-scaled DCs (a scalable face is chosen):
  System / MS Sans Serif no longer come out as 1x glyphs with 2x advances.
Probe: gdi-scaling-combo-fixed.png (same as the unscaled layout, crisp).
Photoshop: gdi-scaling-photoshop-stage2b.png, combo texts complete.
#46 check (blur tool trail, experiments/photoshop-cs2-46/blurtest-rt.sh
with the trial dialog dismissed): first run 28 px (one leftover outline
circle), later runs 0. Repeated three more times (2026-11-09): 0, 0, 0.
So 5 of 6 runs are clean; the single 28-px run is not reproduced and is
kept as a watch item for stage 3 (window-level copies), not a blocker.

### Stage 2, third step: primitives invariant (2026-11-09)

tests/wine/gdi-scale-prims.c (+ .sh): every non-text primitive on a
GDI-scaled window must equal the exact k x k block upscale of the 96-DPI
drawing (otherwise an application that draws a line over blitted content
leaves a residue, e.g. the line under the themed combo button).
First result (experiments/photoshop-cs2-52/gdi-scaling-prims-1.png, left
exact blocks, right GDI scaling; 2472 differing pixels): XOR shapes drawn
twice vanish (good); pens of width 2 and 3 match; pens of width 0 and 1
stay one device pixel (lines, inside-frame rectangles, ellipse, round
rectangle) instead of k pixels on the block grid. Next: thin pens on
GDI-scaled DCs get width k, aligned to the blocks (lines shifted by k/2,
closed shapes as inside-frame).

Thin pens fixed (2026-11-09, dibdrv/objects.c in dllmgr-52-gdi.patch): a
pen of logical width 0 or 1 (solid, inside-frame, cosmetic dashes,
alternate) on a GDI-scaled DC draws the 96-DPI line (device points
floor-divided by k) into a region and paints it scaled by k, once, so
XOR still cancels. Probe: 2472 -> 920 differing pixels; all thin lines
and thin-pen rectangles now equal the block upscale
(gdi-scaling-prims-2.png). The combo button residue line is gone
(gdi-scaling-combo-thin-pens.png, left exact, right GDI scaling).
Still different, not seen in UI so far (open items): wide pens of odd
logical width (3) are one device pixel off and their caps differ; thin
curves (Ellipse, RoundRect corners) are computed at device resolution, so
they are smoother than the block upscale.
