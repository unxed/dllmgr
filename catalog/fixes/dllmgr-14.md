---
id: dllmgr-14
kind: fix
bug: https://github.com/unxed/dllmgr/issues/14
title: "comctl32 v6: report the whole cell as the large-icon LVIR_ICON rectangle"
dlls: [comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/dllmgr-14.patch
patch_sha256: 45c03ad0daa0540ac9345155a83c07d0961ad555bd3dd7d48d74e2a286af133e
recipe: "fix-it-in-wine: tools/build_one_dll.sh wine-11.0 comctl32_v6"
evidence: https://github.com/unxed/dllmgr/actions/runs/42256224744
results:
  - {check: tests/wine/faststone85.sh browser tile geometry, exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, windows: pass, run: https://github.com/unxed/dllmgr/actions/runs/42256224744}
license: LGPL-2.1-or-later
ai_assisted: true
---

# dllmgr-14

FastStone owner-draws each thumbnail tile inside the rectangle returned by
`LVM_GETITEMRECT(LVIR_ICON)`. Native comctl32 v6 returns the whole cell
(138 px wide for FastStone's 138×144 spacing at 96 DPI). Wine returns only
the centered image (240 px inside a 276 px cell at 192 DPI), so the folder
preview, the `BMP` badges and the selection frame cross the tile border.

The patch changes only the public `LVIR_ICON` rectangle in v6 large-icon view
with a normal image list and no state image list. Painting and hit-testing
keep their image metrics.

## Validation status

Same runner, 192 DPI, FastStone 8.5 x86, Wine 11.0: with the four earlier
fixes the tiles overflow; adding this patch keeps the folder preview, badges
and selection inside each tile (artifact `faststone85-192-comparison`,
`patched` vs `icon-cell`). Not yet compared with Windows for other
views or image list setups. No WineHQ bug yet; see the gate in
[the audit](../../docs/faststone.md).
