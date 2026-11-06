---
id: winehq-59251
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=59251
title: "comctl32: scroll horizontal icon lists with the mouse wheel"
dlls: [comctl32, comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/winehq-59251.patch
patch_sha256: c40bf1874154147e14d89353d4d58d17b1f594234b35c1ea23568f7d504161cc
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32 comctl32_v6"
evidence: https://github.com/unxed/dllmgr/actions/workflows/faststone-research.yml
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-59251

The missing thumbnails are covered by winehq-59609. This separate patch handles wheel events in a horizontal ICON list with no vertical scrollbar. Preserve partial-detent accumulation and direction reversal. This candidate does not yet claim to fix the separately reported slow scrolling at high DPI.

## Validation status

Candidate under review. The research workflow compares Windows, unmodified Wine,
patched Wine and undo. Source compilation alone is insufficient: the patched
module must be loaded as native and the affected FastStone UI must be checked.
FastStone 8.5 at 192 DPI requires its own acceptance; a 7.5 result does not prove it.
See [the audit](../../docs/faststone.md) for unresolved cases and applicability.

## Installation

The per-bug entry points are `scripts/apply-winehq-59251.sh` and
`scripts/undo-winehq-59251.sh`. A downloadable binary release is not yet published;
`--build` explicitly requests local compilation. The combined selection is
`scripts/apply-faststone.sh`, with `scripts/undo-faststone.sh` for rollback.
Use the same `WINEPREFIX` and close FastStone before changing its modules.
