# #46 Blur tool cursor leftovers (2026-11-09, stand, Muffin, 192 DPI)

blurtest.sh: Photoshop with a textured 800x600 image, Blur tool, mouse moved
(no button) across the canvas, canvas compared with the same region before.

| start | changed pixels |
|---|---|
| runtime + proxy | 816 |
| stock Wine + proxy (DLLMGR27_NO_TRAMPOLINE=1) | 816 |
| stock Wine, no proxy (DLLMGR27_OFF=1) | 816 |

So it is Wine itself, not dllmgr. The leftovers are short horizontal and
vertical runs at the top/bottom/left/right extremes of the brush circle
(leftovers-diff-and-zoom.png): the XOR circle is erased except for the edge
rows/columns of its bounding box, i.e. the area re-presented after the erase
looks one (logical) pixel short at the bounding box edges when the
DPI-unaware window is scaled 2x. Next: win32u/winex11 surface flush with
scaling (bounds -> physical rect rounding).

## Cause and fix (2026-11-09)

win32u scaled_surface_flush stretches only the dirty part of a DPI-unaware
window to the screen with STRETCH_HALFTONE. The filter spreads a 1 px line
into the neighbouring screen pixels; the XOR erase re-stretches a slightly
different area, so the spread pixels stay. Runtime with halftone switched off:
0 leftover pixels (816 with it). patches/dllmgr-46.patch: at integer scales
(200 %, 300 %) copy exact pixel blocks (crisp, no spread); other scales keep
halftone with the dirty rectangle grown by 1 px. Stand: 0 leftovers; UI text
crisp. No in-process workaround possible: the scaling happens inside win32u.
