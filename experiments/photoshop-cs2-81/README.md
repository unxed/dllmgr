# #81: document window jumps to y=0 during a corner resize (192 DPI)

State 2026-11-11 (agent cc-rcnb-52ab): cause found, runtime fix written and
checked on the stand; paused on owner request before the full write-up.

## Reproduction (stand :132, Muffin, 3072x1728 at 192 DPI)

t81.sh (fresh copy of prefix-clean + `dllmgr fix photoshop-cs2` with v23,
C:\t46.png 600x450): finds the document window with tests/wine/kids81.c,
presses on its bottom-right corner, moves the pointer. FAST=40 moves it in
40 small steps without pauses (like a hand) and logs the X position/size of
the document's client window after each step (steps-*.txt: step, cursor y,
client x, y, width, height); CAP=1 records the screen at 25 fps.

- The document window (class PSDocC) is an owned top-level popup, not an MDI
  child: it has its own X window, framed by Muffin (as in the owner's video).
  The corner is Muffin's frame border, so Muffin does the interactive resize.
- Slow steps (1 s pauses): no bug. Fast steps (FAST=40, DY=540): heights
  flicker (a configure ~180 px too tall now and then), and once the window
  reaches the bottom of the screen Muffin pushes it up: client y 238 -> 215
  -> 178 -> 104 (v23, steps-v23.txt; frame before-v23-step40-50pct.png: the
  document over the menu and options bar). The owner's Cinnamon panel makes
  the bottom closer, so on his screen it ends at y=0.

## Cause (winex11 trace, +x11drv)

On each ConfigureNotify from the WM's resize Wine reports the new rect to
Win32 (WM_WINE_WINDOW_STATE_CHANGED -> SetWindowPos). Photoshop is
DPI-unaware: the rect is mapped to logical units (map_rect_raw_to_virt),
so an odd physical size (1245 px) becomes 622.5 -> 623 -> 1246 px. The
driver then sees a rect one pixel off the X config and sends a
ConfigureRequest ("requesting config ... 1416,1182" after "config 1415,1181")
in the middle of the WM's resize. Muffin applies the request on top of its
own resize: every round the window grows ~37 px more than the pointer
("mismatch config" chain in the log), until it hits the screen bottom and is
moved up. Photoshop itself never calls SetWindowPos on the document during
the drag (relay of SetWindowPos/MoveWindow/DeferWindowPos).

## Fix: patches/dllmgr-81.patch (winex11, runtime)

When a SetWindowPos reports a WM config (flag set in
window_update_client_config) and the resulting rect differs from the
current X config only by the DPI rounding (ceil(scale/2) px per edge, 1 px
at 200 %), sync_window_position keeps the X config and requests nothing.
The window's own SetWindowPos calls are unchanged. DLLMGR81_OFF=1: Wine's
behaviour. Built on top of rt80 (v23 + dllmgr-80) as $B/rt81 (only
winex11.so differs).

## Before/after (FAST=40, DX=600, DY=540)

| runtime | client y during drag | config requests during drag | final client |
|---|---|---|---|
| v23 | 238 ... 215, 178, 104 (pushed up) | one per ConfigureNotify | 1815x1456 at y=215 |
| rt81 = rt80 + dllmgr-81 | 238 at every step | 0 ("keeping WM config" instead) | 1800x1443 at y=238 |

Crops: before-v23-step40-50pct.png, after-rt81-step40-50pct.png (step 40,
left 2000 px of the screen, 50 %).

## Left

- Not yet done: the build-script lines (tests/wine/app-isolation-build.sh
  after dllmgr-80: apply line, cp list, SOURCE.txt line); the DLLMGR81_OFF=1
  run on rt81 (should match v23); the CAP=1 recordings (drag.mp4) for a
  frame-by-frame before/after; a Windows comparison is not needed for the
  cause (no WM on Windows), possibly for upstream wording.
- Still visible with the fix: a thin black strip at the newly exposed right
  and bottom edge for a frame while the pointer moves (the #47 mechanism:
  the X window grows before Photoshop's repaint is flushed). Not the y=0 bug.
- Upstream: the 1-px feedback loop with DPI scaling of unaware windows is a
  WineHQ candidate (retest on wine.git master first), plus a possible Muffin
  note (applies a client ConfigureRequest during an interactive resize).
  Not yet in docs/upstream-outbox.md.
