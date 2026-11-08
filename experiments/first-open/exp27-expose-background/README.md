# #27 mechanism: expose of a never-painted surface + black X background

Research only (2026-11-08, sandbox stand, see results.txt). Not a fix.

The white phase is Wine flushing a window surface the app has not painted
yet. `window_surface_create()` (win32u/dce.c) fills new surface bits with
`0xff`; on X `Expose`, `expose_window_surface()` (win32u/window.c) adds the
exposed rect to `surface->bounds`, so the next `window_surface_flush()` sends
that white to X before the app's WM_PAINT. Before any flush the X window
itself shows its `background_pixel` 0, i.e. black (also what the rejected
ClientSideGraphics=N run showed).

Native Windows keeps the old screen content until the app paints. The
env-gated research patch shows that only both changes together reproduce it:

- A: expose does not dirty the surface -> white gone, black stays;
- B: X background `None` -> black gone before the first flush, white stays;
- A+B: the popup keeps the underlay at every stage, identical to Windows.

A as written is NOT shippable: for a surface that already holds valid app
pixels, expose must still flush them (e.g. after the window was covered),
and A drops that. A correct change must skip only areas never drawn since the
surface was created (or initialise from screen content). Next: such a
"painted region" variant, regression checks for occlusion/redraw, then the
real FastStone first-open probe (32-bit, i386-unix build) at 192 DPI.

## Status / continuation (2026-11-08 18:50)

- Proper A design (not yet coded): expose stores rects in a new
  `surface->exposed` instead of `bounds`; each flush accumulates app drawing
  (`bounds`) into a new `surface->painted`; flush sends
  `bounds ∪ (exposed ∩ painted)`, so never-painted pixels never reach X.
  Plus B (X background `None`). Simplification: `painted` is one bounding
  rect, not a region (two painted corners mark the middle painted too).
  Adding fields to `struct window_surface` needs win32u.so and winex11.so
  rebuilt together (driver structs embed it); fine for a Wine source patch.
- Regression gate is valid now: `tests/wine/window-occlusion.sh` runs
  `window-occlusion.c`, covers the centre with an external `xlogo` (an
  in-process second popup never got an X window), uncovers it and judges by
  the X server's pixel. Stock: `xuncovered F0CC5A verdict=pass`; naive A:
  `000000 verdict=FAIL`. The probe's own GetPixel said yellow in both cases
  (F18), so screen-DC sampling is not trusted for this gate.
- Then: i386 build (FastStone 8.5 is PE32 and stock WineHQ uses i386-unix),
  real first-open probe (tests/wine/first-open-probe.c) at 192 DPI.
- Sandbox build recipe: `apt` deps in docs/sandbox-stand.md; Wine source
  `git clone --depth 1 --branch wine-11.0 https://github.com/wine-mirror/wine`
  (= db11d0fe); `configure --enable-win64 --without-<extras>` in a separate
  build dir; `make dlls/win32u/win32u.so dlls/winex11.drv/winex11.so`
  (~40 s incremental); copy `/opt/wine-stable` to a scratch dir and drop the
  .so files into its `lib/wine/x86_64-unix/`. Run with `STAND_WM=metacity`.

## Mode 2 result (2026-11-08 18:55)

`DLLMGR_EXP27=2 DLLMGR_EXP27B=1` (painted-rect expose + X background None)
matches native Windows on the popup diagnostic at every stage AND passes the
occlusion gate (old pixels re-sent after uncover). Naive A fails that gate.
Patch: research-env-gated.patch (adds `exposed`/`painted` to
`struct window_surface`, so win32u.so and winex11.so must be rebuilt
together). Still research: env-gated, bounding-rect approximation, B changes
every X window's background (GL/Vulkan client areas, resize gaps, other WMs
untested). Next: i386 build and the real FastStone first-open probe judged by
X pixels (F18), then other WMs (Muffin) and a resize check.
