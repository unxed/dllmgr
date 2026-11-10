---
id: dllmgr-63
kind: fix
bug: https://github.com/unxed/dllmgr/issues/63
title: "comctl32 v6: themed combo drop button as on Windows (DropDownButtonRight part and geometry)"
dlls: [comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/dllmgr-63.patch
patch_sha256: f765cd6af96d5b91f3b76c9b9a07046b080d778db7c73b76581579c51409c178
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32_v6"
binaries: https://github.com/unxed/dllmgr/releases/tag/faststone-v5
evidence: https://github.com/unxed/dllmgr/tree/main/experiments/faststone-63
license: LGPL-2.1-or-later
ai_assisted: true
---

# FastStone path dropdown button frame

## Problem

The drop button of the folder-path box above the thumbnails shows a frame
without its left side: grey in the normal state, blue on hover.

## Windows behavior

Themed Windows (the #21 captures at 96 DPI) draws the button with no frame
in the normal state, only the glyph; on hover the whole button gets a frame.
The button spans client width - SM_CXVSCROLL to client width - 1, next to
the 1 px theme border.

## The fix in words

In comctl32 v6, for themed combo boxes:
- draw the drop button with the CP_DROPDOWNBUTTONRIGHT part when the theme
  defines it, as Windows does since Vista;
- place the button from client width - SM_CXVSCROLL to client width - 1.

FastStone paints its text field itself up to client width - SM_CXVSCROLL,
after the combo. Wine's button started 2 px (192 DPI) further left, under
that paint. The classic (unthemed) paint and geometry do not change.

## Results

Stand, actual FastStone 8.5 at 192 DPI under the private runtime
(experiments/faststone-63/t63.sh): normal state shows only the glyph; hover
shows the full frame on all four sides. The patch composes with dllmgr-21
(same file, separate hunks).
