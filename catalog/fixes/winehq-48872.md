---
id: winehq-48872
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=48872
title: "comctl32: return a usable rectangle for an empty icon label"
dlls: [comctl32, comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/winehq-48872.patch
patch_sha256: 5088c1e05ab76663cad8527a4b2d432d52557513762f74124da11af51027144e
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32 comctl32_v6"
evidence: https://github.com/unxed/dllmgr/actions/workflows/faststone-research.yml
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-48872

FastStone draws file names itself inside the rectangle returned by `LVM_GETITEMRECT(LVIR_LABEL)`. Wine returns zero width for an empty control label. The patch changes the public label/select rectangle without changing painting metrics: selected items with empty text must not acquire a painted empty label. This avoids the visual regression discussed in MR 10093.

## Validation status

Candidate under review. The research workflow compares Windows, unmodified Wine,
patched Wine and undo. Source compilation alone is insufficient: the patched
module must be loaded as native and the affected FastStone UI must be checked.
FastStone 8.5 at 192 DPI requires its own acceptance; a 7.5 result does not prove it.
See [the audit](../../docs/faststone.md) for unresolved cases and applicability.

## Installation

The per-bug entry points are `scripts/apply-winehq-48872.sh` and
`scripts/undo-winehq-48872.sh`. A downloadable binary release is not yet published;
`--build` explicitly requests local compilation. The combined selection is
`scripts/apply-faststone.sh`, with `scripts/undo-faststone.sh` for rollback.
Use the same `WINEPREFIX` and close FastStone before changing its modules.
