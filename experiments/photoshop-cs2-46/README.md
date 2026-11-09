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
