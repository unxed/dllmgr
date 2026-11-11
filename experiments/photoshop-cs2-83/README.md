# #83: halo of garbage pixels around the Opacity/Flow slider popup

2026-11-11, agent cc-rcnb-52ab. Stand :134 (Xvfb 3072x1728 at 192 DPI,
Muffin), fresh copies of prefix-clean with `dllmgr fix photoshop-cs2`.

## Reproduction

t83.sh: start Photoshop CS2 (trial "Continue", the F26 box closed), click
the Brush tool in the toolbox, click the arrow next to Opacity (757,137) or
Flow (935,137), screenshot. Options: VIA_DLLMGR=1 (start with `dllmgr run`,
the owner's way), EXTRA (env, e.g. DLLMGR27_DEBUG=1), PROBE (window list),
CAP (tests/wine/screencap83.c: screen-DC read of a rectangle).

- Without the dllmgr-27 proxy, or with it and `DLLMGR27_NO_PREFILL=1`: the
  popup has a clean 3D frame (2 logical px: white top/left, grey 189/158
  right/bottom).
- With the proxy (v21 via `dllmgr run`, and v22 + the current proxy):
  the frame on all four sides shows foreign pixels, on v22 the coloured
  pixels of the menu text, as in the owner's screenshot. Reproduced 4/4.

The popup: class PSFloatC, style 94000040, ex-style WS_EX_TOOLWINDOW,
122x24 logical (244x48 on X), no layered style, no region. Its client area
is inset; Photoshop paints the frame as non-client area.

## Cause

The dllmgr-27 prefill (patches/dllmgr-27/prefill.c, Photoshop build
version.dll) copies the screen under every new caption-less top-level window
on WM_WINDOWPOSCHANGING and draws the copy into the whole window (window DC)
on WM_WINDOWPOSCHANGED. Two faults meet in the popup:

1. Wine sends WM_NCPAINT/WM_ERASEBKGND for a newly shown window inside
   SetWindowPos before WM_WINDOWPOSCHANGED (win32u set_window_pos:
   erase_now, then the message). Photoshop's frame is already painted when
   the copy is drawn over it, and only the client area is repainted later
   (WM_PAINT). So the frame shows the copy.
2. The copy comes from the wrong place. The proxy switches its thread to
   per-monitor awareness and expects physical pixels from GetWindowRect,
   but under Wine a per-monitor-aware thread gets the logical rectangle of a
   DPI-unaware window (tests/wine/dpirect83.c on stock 11.0 and the runtime:
   268,76-390,100 in default, PMA v1 and PMA v2 contexts, while the screen
   DC reports 192 DPI). The screen DC is physical, so the proxy copies the
   122x24 physical pixels at the popup's logical position and the window DC
   (logical) shows them 2x enlarged.

Proof on the owner's screenshot: the frame pixels equal, pixel for pixel
(sum of differences 0), the region at physical (316,72) 122x24 enlarged 2x:
the popup's logical position (popup at 633,144 physical). That region is
the menu bar ("Select", "Filter" in ClearType colours) with the grey line
under it: hence beige/blue/black on three sides and the plain grey bottom.
owner-source-vs-frame.png: top, that menu bar region 3x; bottom, the
owner's popup 3x.

Screen-DC reads themselves are right on the stand: screencap83 (separate
process, per-monitor aware) of the popup rectangle matched `import` 0/11712
pixels before and while the popup was open.

## Fix (in-process, patches/dllmgr-27/prefill.c)

In the Photoshop build (DLLMGR27_CAPTIONLESS_ONLY) WS_EX_TOOLWINDOW windows
get no snapshot. Photoshop's tool windows (palettes, toolbox, options bar,
its slider popups) paint themselves completely; the splash, the one window
that needed the snapshot, is not a tool window (and since #43 it is
adopted and gets no snapshot anyway). FastStone's msimg32
build is unchanged. Works on any Wine; ships with the next runtime build
(app-isolation.yml builds the proxy from prefill.c). No Wine patch.

## Before / after

Same prefix, same runtime, only version.dll differs (current proxy with and
without the change):

- opacity-before-after.png (v22, direct start): top before (menu text
  pixels in the left frame column, white elsewhere), bottom after. After is
  identical (0 px) to the run with DLLMGR27_NO_PREFILL=1.
- flow-before-after.png (v21 via `dllmgr run`, owner's settings): Flow
  popup, before (white frame, black block), after (3D frame).
- Whole screen before the popup opens: identical with and without the
  change (palettes, toolbox, options bar).

## Left over

- Wine: GetWindowRect (and the other window-rectangle calls) from a
  per-monitor-aware thread return logical coordinates for DPI-unaware
  windows. Windows reference: dpirect83 in windows-probes.yml (after
  screendc80 setscale). Listed in docs/upstream-outbox.md.
- The prefill's own logical/physical mix (fault 2) remains for windows
  that still get a snapshot; docs/sandbox-findings.md F30.
