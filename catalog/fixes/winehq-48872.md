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
results:
  - {check: tests/wine/faststone85.sh browser names, exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, windows: pass, run: https://github.com/unxed/dllmgr/actions/runs/42236384573}
license: LGPL-2.1-or-later
ai_assisted: true
---

# winehq-48872

## Problem

In a list-view in icon view, an item whose own text is empty gets a
zero-width rectangle from `LVM_GETITEMRECT(LVIR_LABEL)` and no label part in
`LVIR_SELECTBOUNDS`. Applications that keep the text elsewhere and draw the
name themselves inside that rectangle show no names. FastStone does this for
every file and folder under its thumbnails.

## Windows behavior (measured)

comctl32 v6, 32×32 icons, 96 DPI, item text `''`: `LVIR_LABEL` is
(1,37)–(76,54), the full item width under the icon, and a selected item paints
no pixels there. Text `' '` paints a selection background (119 pixels).

## The fix, in words

In `LISTVIEW_GetItemRect`, icon view, modes `LVIR_LABEL` and
`LVIR_SELECTBOUNDS`, when the item text is empty or a callback: return a label
rectangle as wide as the item (`nItemWidth`), starting below the icon
(`ICON_TOP_PADDING_HITABLE + iconSize.cy + ICON_BOTTOM_PADDING`), one text line
high (`ntmHeight + HEIGHT_PADDING`); for `LVIR_SELECTBOUNDS` unite it with the
existing rectangle. Painting metrics are unchanged, so an empty selected
label still paints nothing. This keeps the geometry of MR 10093 without its
painted selection rectangle.

## Results

FastStone 8.5 at 192 DPI: the first label's width goes from 0 to 276 pixels
and names appear under files and folders, including Cyrillic ones. The
controls fixture `--check-label` checks a usable rectangle and no painted
pixels. See `results` and [the audit](../../docs/faststone.md).

## Installation

Part of the FastStone recipe (`dllmgr fix faststone`). The per-bug entry
points are `scripts/apply-winehq-48872.sh` and `scripts/undo-winehq-48872.sh`.
