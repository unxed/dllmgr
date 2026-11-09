---
id: winehq-60721
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=60721
title: "win32u/winex11: do not present undrawn window surface areas on first expose"
dlls: [win32u, winex11]
programs: [FSViewer.exe, Photoshop.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/winehq-60721.patch
patch_sha256: 451b543dbd32ecb88755865f4a60f18c69b911b1f6063a8018ef22b870ca7d46
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 win32u winex11"
evidence: https://github.com/unxed/dllmgr/actions/runs/42529718835
results:
  - {check: "FastStone first-open no white flash (tests/wine/first-open.sh)", exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/36#issuecomment-6725350290"}
  - {check: "Photoshop CS2 splash margin shaped, no stale grey frame", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/36#issuecomment-6734637591"}
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-60721

## Problem

When a window is shown for the first time, Wine presents the entire window
surface (filled with 0xff white) before the application has painted anything.
This causes a white flash on first open (FastStone fullscreen viewer) and a
white rectangle around the Photoshop CS2 splash screen.

On Windows without DWM, a newly shown window shows the previous screen
contents until the application paints. Wine was showing a white (or black in
older Wine) fill instead.

## Windows behavior

(measured) A fresh window on Windows shows the desktop/wallpaper or the
overlapped window contents until the first WM_PAINT. No solid fill is visible.

## The fix, in words

Two coordinated changes:

1. **win32u (window_surface)**: Track `exposed` (areas waiting to be
   presented) and `painted` (bounding rect of all drawing so far) separately
   from `bounds`. In `window_surface_flush`, only present the intersection of
   `exposed` and `painted`. A fresh surface has `painted` empty, so nothing
   is presented on the first Expose.

2. **winex11 (window creation)**: Create X windows with `background_pixmap =
   None` instead of `background_pixel = 0`. This keeps the previous screen
   contents visible until the first paint, matching Windows behavior.

The `window_surface` struct grows two `RECT` fields (`exposed`, `painted`),
so `win32u.so` and `winex11.so` must be rebuilt together.

## Results

- FastStone 8.5 first-open: no white flash (3/3 passes on stand, Metacity
  192 DPI).
- Photoshop CS2 splash: the margin becomes see-through and live; no stale
  grey frame when the main window is minimized during startup.
- Tested on stock Wine 11.0, Xvfb/Metacity 192 DPI; also works on the
  private runtime with compositing WM (Muffin).

See [#27](https://github.com/unxed/dllmgr/issues/27) and [#36](https://github.com/unxed/dllmgr/issues/36) for the full investigation.