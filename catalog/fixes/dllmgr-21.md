---
id: dllmgr-21
kind: fix
bug: https://github.com/unxed/dllmgr/issues/21
title: "comctl32 v6: keep themed combo button painting in sync with its open/closed list"
dlls: [comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/dllmgr-21.patch
patch_sha256: 53e141e30cada06752749fb4af5595386054e4b759322ee847a1fd6c66bf03a9
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32_v6"
binaries: https://github.com/unxed/dllmgr/releases/tag/dllmgr-21-v2
evidence: https://github.com/unxed/dllmgr/actions/runs/42499612512
results:
  - {check: tests/wine/check-path-dropdown.py actual FastStone themed path button, exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: https://github.com/unxed/dllmgr/actions/runs/42499612512}
license: LGPL-2.1-or-later
ai_assisted: true
---

# FastStone path dropdown button

## Problem

The folder-path dropdown above the thumbnails opens on mouse down and remains
open after mouse up. Wine changes the arrow button's pressed appearance on
release even though the list remains open, making it appear to pop back up.
This is separate from the owner's old, severe, intermittent corruption of the
path row, which has not been reproduced or fixed.

## Windows behavior

Official FastStone 8.5 x86 on native Windows, at 96 DPI with a 900x600 client
area: the themed button changes 330 pixels on hover-to-down and **zero** on
down-to-up while the list remains open. The public pressed state and capture
still clear on release. Native Windows and Wine have the same 481x24 control
size and the same open/close state transitions. OS theme colors differ, so
whole-button Windows/Wine color equality is not asserted.

## The fix in words

When choosing the themed dropdown button's visual state in comctl32 v6,
consider an open dropdown list as well as a held button when selecting the
pressed appearance. Do not change public pressed/capture state, notifications,
input handling, the classic paint path or list visibility.

## Results

Stock Wine fails the actual-app pixel check at 96/192 DPI. With this isolated
change, and with the four existing list-view patches composed into the same
module, the button is stable across hold/release while the list stays open.
Native loading and byte-exact original-DLL restoration passed in CI
[42416643457](https://github.com/unxed/dllmgr/actions/runs/42416643457) at
8ea884f7137bda4e6cb23a11dfd73b0dae45f6b8. See
[the research log](../../experiments/path-dropdown/README.md) for failures and
scope. An earlier build of the same patch series passed on the owner's actual prefix at 192 DPI, with
native loading confirmed; original DLLs, journal and installed FastStone
settings were restored after the temporary test. The owner's visual acceptance
is still pending in #21; the intermittent row corruption remains open.

Apply this individual fix with `scripts/apply-dllmgr-21.sh`; undo with
`scripts/undo-dllmgr-21.sh`. Individual DLL selections replace other selections
of that module; use `dllmgr fix faststone` for the composed set.

## Second-click closing correction (2026-11-08)

The owner clarified a second-click close with no intervening pointer movement:
the list disappears but the button stays blue until movement. This reproduces
with the earlier v3 correction. Closing from the listbox could repaint only the
text rectangle, omitting the now state-dependent themed button. The complete
fix includes the button in themed close redraws; classic drawing and public
state remain unchanged.

The focused real-app gate fails on v3 (pressed→closed0 changed pixels) and
passes with the correction isolated and composed at96/192DPI (300/1216 changed
pixels immediately on closing). The Windows comparison passes. Exact binaries,
source and checksums: individual `dllmgr-21-v2`, composed `faststone-v4`.
The local ID remains stable for installed recipe compatibility. Upstream
words-only report: [Wine60720](https://bugs.winehq.org/show_bug.cgi?id=60720#c0).
Owner acceptance of the newly installed close correction remains pending;
the old severe path-row corruption is a separate unresolved issue.
