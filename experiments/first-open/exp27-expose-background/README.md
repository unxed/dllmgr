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
