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

FastStone 7.5 passes a red GDI+ pen but its pencil draws black. The minimal reproducer isolates a 24-bit DIB and an inherited `R2_BLACK` raster operation. Windows draws red and preserves the caller's raster operation; Wine draws black. Reset ROP2 inside the saved DC state used for GDI+ drawing, then restore that state. Test 24/32-bit surfaces and several ROP modes.

## Validation status

Candidate under review. The research workflow compares Windows, unmodified Wine,
patched Wine and undo. Source compilation alone is insufficient: the patched
module must be loaded as native and the affected FastStone UI must be checked.
FastStone 8.5 at 192 DPI requires its own acceptance; a 7.5 result does not prove it.
See [the audit](../../docs/faststone.md) for unresolved cases and applicability.

## Installation

The per-bug entry points are `scripts/apply-winehq-48874.sh` and
`scripts/undo-winehq-48874.sh`. A downloadable binary release is not yet published;
`--build` explicitly requests local compilation. The combined selection is
`scripts/apply-faststone.sh`, with `scripts/undo-faststone.sh` for rollback.
Use the same `WINEPREFIX` and close FastStone before changing its modules.
