---
id: dllmgr-44
kind: fix
bug: https://github.com/unxed/dllmgr/issues/44
title: "winex11: scale custom cursors of DPI-unaware apps like Windows does"
dlls: [winex11]
programs: [Photoshop.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/dllmgr-44.patch
patch_sha256: 7c88e522a39fafcd35cf8d16c34bbfe2dd3d4beab0f497342183718680f4a5a2
recipe: "private runtime: wine-11.0 + wine-11.0-app-isolation.patch + winehq-60721.patch + dllmgr-43.patch + dllmgr-44.patch"
evidence: https://github.com/unxed/dllmgr/issues/44
results:
  - {check: "custom tool cursors scaled from 32x32 to 64x64 at 192 DPI", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/44"}
license: LGPL-2.1-or-later
ai_assisted: true
---

# dllmgr-44

## Problem

Photoshop CS2's custom cursors (tool cursors) are very small, close to
unusable, on the owner's 192 DPI setup (Wine LogPixels 192, Cinnamon).
Expected (Windows at 200%): a DPI-unaware app's cursors are scaled with the
app.

## Windows behavior

(measured) On Windows at 200% scaling, a DPI-unaware application's custom
cursors are scaled up by the system (e.g., 32x32 -> 64x64). The hotspot
coordinates are also scaled proportionally.

## The fix, in words

Changes to `dlls/winex11.drv/mouse.c`:

1. **Cursor scale calculation**: For each window, compute the scale factor
   as `monitor_dpi / window_dpi` (where `window_dpi` comes from
   `NtUserGetDpiForWindow` and `monitor_dpi` from `NtUserGetWinMonitorDpi`
   with `MDT_RAW_DPI`). Only scale up (never shrink), as Windows does for
   DPI-unaware apps.

2. **Separate cursor cache for scaled cursors**: A new `cursor_scaled_context`
   X context stores scaled cursors separately from unscaled ones. The same
   cursor handle can have both a 1x and a scaled version cached.

3. **Bitmap stretching**: When creating a scaled cursor, the mask and color
   bitmaps are stretched using `NtGdiStretchBlt` (nearest neighbour when
   enlarging). Hotspot coordinates are scaled proportionally.

4. **Integration points**: `X11DRV_SetCursor` (called when setting a
   window's cursor) and `grab_clipping_window` now compute the scale for the
   target window and use the appropriate cache. `X11DRV_DestroyCursorIcon`
   cleans up both caches.

The patch is controlled by `DLLMGR44_NO_CURSOR_SCALE=1` (disables scaling).

The patch is part of the private runtime built by CI, which includes:
- `wine-11.0-app-isolation.patch`
- `winehq-60721.patch`
- `dllmgr-43.patch`
- `dllmgr-44.patch`

## Results

Owner's stack: Cinnamon, X11, Muffin (compositing WM), 192 DPI. Stand: Wine
11.0, Xvfb 3072x1728 @192 DPI, Metacity and Muffin. Custom cursors now
scale from 32x32 to 64x64 at 192 DPI, matching Windows behavior for
DPI-unaware apps. Tested with `tests/wine/cursor-scale.sh` probe.

See [#44](https://github.com/unxed/dllmgr/issues/44) for the full investigation.