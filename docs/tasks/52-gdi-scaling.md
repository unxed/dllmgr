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
