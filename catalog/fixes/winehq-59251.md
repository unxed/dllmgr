---
id: winehq-59251
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=59251
title: "comctl32: scroll horizontal icon lists with the mouse wheel"
dlls: [comctl32, comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/winehq-59251.patch
patch_sha256: 8eb2a421cb21cedfc4db8a5ec0fe3d4222799499079c0160b9fea34f13ae4403
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32 comctl32_v6"
evidence: https://github.com/unxed/dllmgr/actions/workflows/faststone-research.yml
results:
  - {check: tests/wine/faststone85.sh browser wheel (item0 px per detent), exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, windows: pass, run: https://github.com/unxed/dllmgr/actions/runs/42263591184}
  - {check: "owner's desktop: fullscreen strip scrolls with the wheel", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/8#issuecomment-6693158826"}
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-59251

## Problem

In a list-view in icon view (`LVS_ICON`), the mouse wheel does not behave
like Windows:

1. A list that grows horizontally (left-aligned icons, horizontal scrollbar
   only, e.g. FastStone's fullscreen thumbnail strip) does not scroll at all:
   Wine always scrolls vertically.
2. Where it scrolls, Wine moves a fixed 37 pixels per `WM_MOUSEWHEEL`,
   whatever the wheel delta: half a detent, one detent and two detents all
   move 37 pixels, and a zero delta moves too.

The missing thumbnails in the same strip are a different defect
(winehq-59609).

## Windows behavior (measured)

comctl32 v6, three wheel lines (the default):

- Deltas accumulate; nothing moves until a full `WHEEL_DELTA` (120) is
  reached, and leftovers are dropped when the direction changes.
- Each detent scrolls `lines × spacing / 2` pixels on the scrolled axis,
  where `spacing` is the icon spacing on that axis (`LVM_GETITEMSPACING`) and
  `lines` comes from `SPI_GETWHEELSCROLLLINES`; at most one page.
- The scrolled axis is horizontal when the control has a horizontal
  scrollbar and no vertical one, otherwise vertical.

Evidence: 32×32 icons with 74-pixel spacing → 111 pixels per detent (this is
where Wine's constant 37 = 74 / 2 comes from); FastStone's 138×144 cells at
96 DPI → 207 pixels horizontally and 216 vertically. Comctl32 v5 is
unchanged by this fix.

## The fix, in words

In `LISTVIEW_MouseWheel`, for `LV_VIEW_ICON`: choose the axis as above;
accumulate the delta in the existing `cWheelRemainder` (reset on direction
change); for each whole detent, scroll `lines × (item width or height) / 2`
pixels (falling back to 37 when the size is unknown), capped at one page;
call the horizontal or vertical scroll routine with that amount. Zero or
partial deltas do nothing. The v5 build keeps 37 pixels per detent but uses
the same axis choice and accumulation.

## Results

FastStone 8.5, Wine 11.0, 192 DPI, item 0 position after each event
(½, ½, 1, 2 detents): unpatched 37/37/37/37 pixels; patched 0/426/426/852
(426 = 3 × 284 / 2); Windows at 96 DPI 0/216/216/432. The strict controls
fixture checks both axes, zero and half-detent deltas and Ctrl. See
`results` in the frontmatter and [the audit](../../docs/faststone.md).

## Installation

Part of the FastStone recipe (`dllmgr fix faststone`). The per-bug entry
points are `scripts/apply-winehq-59251.sh` and `scripts/undo-winehq-59251.sh`.
Use the same `WINEPREFIX` and close FastStone before changing its modules.
