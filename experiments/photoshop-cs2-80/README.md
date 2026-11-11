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

Relay of the drawing calls (Wine's own user32/gdi32 only, RelayInclude
list; a black-box API trace, Photoshop.exe was not disassembled): on
WM_NCLBUTTONDOWN in the palette's title, Photoshop takes
GetWindowDC(GetDesktopWindow()), selects a clip region (SelectClipRgn),
SetROP2(R2_XORPEN) and draws the outline with
FrameRgn(desktop DC, rgn, brush, 1, 1), polling GetCursorPos in a loop. All
coordinates are the virtualized (96 DPI) ones it gets from GetCursorPos and
GetWindowRect. The release moves the palette with SetWindowPos, which Wine
scales correctly, hence the right final position.

## 2026-11-11: Windows does the same (no bug in Wine as such)

tests/wine/screendc80.c (windows-probes run 43025940632, output in
windows-screendc80.txt): a DPI-unaware thread draws an R2_NOT outline and a
PatBlt(DSTINVERT) at logical 100,100-300,250 on GetDC(NULL),
GetWindowDC(GetDesktopWindow()), GetDCEx(desktop, DCX_WINDOW|DCX_CACHE|
DCX_LOCKWINDOWUPDATE) and CreateDC("DISPLAY"); a per-monitor-aware thread
captures the screen before and after. The probe first switches the runner to
1920x1080 and its largest scale (175 %, 168 DPI) with
DisplayConfigSetDeviceInfo and measures in a fresh process.

- Windows at 175 %: the unaware thread sees a 1097x617 screen (SM_CXSCREEN,
  desktop rect, HORZRES) but the drawing lands 1:1 at physical
  100,100-300,250, not scaled. So the same Photoshop outline would be off on
  Windows too (at 1/1.75 of the position).
- Wine v23 at 192 DPI (wine-screendc80.txt): identical, physical
  100,100-300,250, screen 1536x864 for the thread.

So stock Wine matches Windows; no WineHQ report is owed. The fix below is a
deliberate dllmgr improvement for DPI-unaware applications.

## Fix: patches/dllmgr-80.patch (win32u, runtime)

A desktop window DC (GetDC(0), GetWindowDC(GetDesktopWindow()),
GetDCEx(desktop, ...)) obtained by a thread whose DPI differs from the
physical screen (DPI-unaware, or system-aware with another DPI) gets a
hidden scale from the thread's virtual screen to the physical one
(get_virtual_screen_rect of the thread DPI vs MDT_RAW_DPI): it is folded
into the DC's world-to-viewport transform (DC_UpdateXforms) and clip regions
selected into such a DC are scaled too (NtGdiExtSelectClipRgn). NtUserGetDCEx
sets or clears it on every call, since cache DCs are shared. Region painting
(FrameRgn/FillRgn/PaintRgn), lines, PatBlt/BitBlt and GetPixel all go through
the transform, so the outline lands at the palette's physical place and size
(a 1-logical-px frame becomes 2 px). CreateDC("DISPLAY") is not changed.
DLLMGR80_OFF=1 gives Wine's (= Windows') behaviour.
Side effects: on such a DC LPtoDP/DPtoLP show the scale and GetClipRgn
returns physical units; screen reads by unaware threads (BitBlt/GetPixel from
GetDC(0)) now read the right place, scaled, instead of the top-left quarter.

Results (wine-screendc80.txt): rt80 (v23 + dllmgr-80): the outline at logical
100,100-300,250 lands at physical 200,200-600,500; clip box 0,0-1536,864;
with DLLMGR80_OFF=1 back to 100,100-300,250.

## Before/after on the stand (t80.sh, drag 600,300 in 6 steps)

| runtime | outline at step 6 (x edges) | toolbox after release |
|---|---|---|
| v22/v23 | 308..371 (64 px, half position and size) | 616,474 128x884 |
| rt80 = v23 + dllmgr-80 | 616..743 (128 px), top 474 | 616,474 128x884 |

Crops (top-left 1000x1400 px of the screen at step 6, 50 %):
before-v22-drag6-50pct.png, after-fix-drag6-50pct.png. With the fix the
outline matches the toolbox's final place and size at every step (x edges
116/216/316/416/516/616 for steps 1..6); a second run with the final build
(rt80 rebuilt from patches/dllmgr-80.patch as committed) gave the same numbers.

In-process alternative (not done here): the dllmgr-27 proxy could hook
GetDC/GetWindowDC/GetDCEx for the desktop window in the application's
modules and set GM_ADVANCED + a scaling world transform on such DCs, and
scale the regions passed to SelectClipRgn/ExtSelectClipRgn for them. That
would carry the same result to stock Wine; it needs the proxy's import hooks
for six more functions.
