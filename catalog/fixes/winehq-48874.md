---
id: winehq-48874
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=48874
title: "gdiplus: ignore inherited ROP2 when drawing with a GDI pen"
dlls: [gdiplus]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/winehq-48874.patch
patch_sha256: 8a4379e7967b771bc8c2296dd2dd158b6acb6ee6e82abfbbf60fd628e28a5e68
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 gdiplus"
evidence: https://github.com/unxed/dllmgr/actions/workflows/faststone-research.yml
results:
  - {check: tests/wine/pencil.c, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, without: fail, with: pass, windows: pass, run: https://github.com/unxed/dllmgr/actions/runs/42256305651}
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-48874

## Problem

FastStone's pencil in Draw Board always draws black, whatever colour is
selected; other shapes use the colour. The application draws with a GDI+ pen
on a device context whose raster operation is `R2_BLACK` (inherited from its
own GDI drawing). Wine's GDI+ uses that raster operation, so every stroke is
black.

## Windows behavior (measured)

GDI+ ignores the raster operation of the HDC it draws on and leaves the
caller's value unchanged. The probe `tests/wine/pencil.c` draws a red line
with GDI+ on 24- and 32-bit DIBs under several ROP2 modes: Windows draws red
and keeps the ROP2 in every case; stock Wine draws black under `R2_BLACK`
(2 failures).

## The fix, in words

In GDI+ `prepare_dc`, right after `SaveDC`, set the raster operation to
`R2_COPYPEN`. The `RestoreDC` that ends the drawing returns the caller's
value, so the application's own GDI state is untouched.

## Results

Probe: 0 failures with the fix, as on Windows. Real FastStone 8.5 Draw Board,
default pencil, one stroke across the canvas: Windows red (`ff0000`), stock
Wine 11.0 black (`000000`). The full bundle draws red in CI and on the
owner's laptop. A separate actual-app run with **only** the GDI+ candidate,
stock comctl32 and a freshly started wineserver draws red (`ff0000`, 3642
pixels), with native GDI+ / builtin comctl32 load evidence. Undo restored the
installed bundle, override values, managed state and settings. See
`experiments/local-validation/README.md` for the earlier stale-server failure
and the successful cold comparison. User visual acceptance remains pending.

## Installation

Part of the FastStone recipe (`dllmgr fix faststone`). The per-bug entry
points are `scripts/apply-winehq-48874.sh` and `scripts/undo-winehq-48874.sh`.
