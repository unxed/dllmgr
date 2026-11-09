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
evidence: https://github.com/unxed/dllmgr/issues/27#issuecomment-6725041423
results:
  - {check: "tests/wine/first-open-x.sh FastStone first-open X-pixel verdict, no interruption", exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/27#issuecomment-6725041423"}
  - {check: "tests/wine/window-occlusion.sh occlusion regression gate (X-pixel verdict)", exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/27#issuecomment-6725041423"}
  - {check: "owner's laptop: FastStone normal launch, no first-open flash (private runtime v3)", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/27#issuecomment-6728896876"}
  - {check: "experiments/ps-focus/menu-burst.sh Photoshop CS2 menus, no black frame before first paint (private runtime)", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/45#issuecomment-6737112678"}
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-60721

## Problem

When a window is shown for the first time, Wine presents the entire window
surface (filled with 0xff white) before the application has painted anything.
This causes a white flash on first open (the FastStone fullscreen viewer).

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

- FastStone 8.5 first-open: no white flash. Judged by X server pixels
  (`tests/wine/first-open-x.sh`), not by Wine's screen DC, which can report
  surface contents that never reached X. Stock Wine 11.0 showed image → black
  ~20 ms → white ~90–170 ms → image; with this patch there is no interruption
  (2/2 runs on the stand, Metacity 192 DPI).
- Occlusion regression gate (`tests/wine/window-occlusion.sh`, X-pixel
  verdict): passes. The naive "ignore every expose" variant fails it.
- Owner's laptop (2026-11-09): FastStone launches normally without the
  first-open flash on private runtime v3.
- Delivery: this patch ships in the private runtime
  (`scripts/private-runtime.json`), because `win32u.so` and `winex11.so` have
  a unix part and cannot be replaced in a prefix.
- Photoshop CS2 menus under a compositing WM: the black frame before the
  first paint is gone on the private runtime (0/40 bad frames, Muffin;
  5/40 and 6/40 with stock Wine, with and without the proxy). See
  [#45](https://github.com/unxed/dllmgr/issues/45).

Not covered: the Photoshop CS2 splash. Its white rectangle comes from
Photoshop compositing the splash over its own window's initial 0xff surface;
the splash itself is fixed by the version.dll prefill proxy
([#36](https://github.com/unxed/dllmgr/issues/36)), not by this patch. The
proxy shapes the splash from the card's own alpha, so the margin is gone
there as well (private runtime v5, owner check 2026-11-09; see
[experiments/ps-focus](../../experiments/ps-focus/README.md)).

See [#27](https://github.com/unxed/dllmgr/issues/27) for the full investigation.