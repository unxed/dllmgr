# #80: palette drag outline drawn off its real position (192 DPI)

## 2026-11-11: reproduced on the stand

t80.sh (stand :132, Muffin, 3072x1728 at 192 DPI, runtime v22, fresh copy
of prefix-clean, C:\t46.png): toolbox at 16,174 128x884 (physical), drag
by its title strip 600,300 px in 6 steps. The outline Photoshop draws while
dragging is at half the coordinates and half the size: at step 6 its
vertical edges are at x=308 and x=371 (64 px wide), while the toolbox
would be at x=616 (128 px wide). After the release the toolbox lands at
616,474, i.e. where the pointer put it. So the outline is drawn in logical
(DPI-virtualized, 96 DPI) coordinates on a surface that is physical.

Relay of the drawing calls (Wine's own user32/gdi32 only): on
WM_NCLBUTTONDOWN in the palette's title, Photoshop takes
GetWindowDC(GetDesktopWindow()), SetROP2(R2_XORPEN) and polls GetCursorPos
in a loop while drawing the outline on that desktop DC.

Windows reference: tests/wine/screendc80.c in windows-probes.yml (draws an
outline at logical coordinates on screen DCs from an unaware thread and
finds where it lands in physical pixels, after raising the monitor scale).
