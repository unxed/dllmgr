---
id: winehq-59609
kind: fix
bug: https://bugs.winehq.org/show_bug.cgi?id=59609
title: "comctl32: LVM_GETITEMPOSITION returns client coordinates instead of view coordinates in ICON/SMALLICON views (breaks FastStone Image Viewer)"
dlls: [comctl32, comctl32_v6]
programs: [FSViewer.exe]
wine: [wine-9.0, wine-11.0]
patch: https://raw.githubusercontent.com/unxed/fix-it-in-wine/main/showcases/59609/fix.patch
patch_sha256: 4c4e4672a06370e612f9305be7cab7a59c8dd7d8638297b1029831a4d0218295
recipe: "fix-it-in-wine: tools/build_one_dll.sh <tag> comctl32 [comctl32_v6]"
binaries: https://github.com/unxed/dllmgr/releases/tag/winehq-59609
evidence: https://github.com/unxed/fix-it-in-wine/actions/workflows/showcase-59609.yml
results:
  - {check: fix-it-in-wine showcases/59609/lvpos.c, wine: wine-9.0, host_arch: x86_64, without: fail, with: pass, windows: pass, run: https://github.com/unxed/fix-it-in-wine/actions/runs/42156695927}
  - {check: fix-it-in-wine showcases/59609/lvpos.c, wine: wine-11.0, host_arch: x86_64, without: fail, with: pass, windows: pass, run: https://github.com/unxed/fix-it-in-wine/actions/runs/42156695927}
  - {check: fix-it-in-wine showcases/59609/lvpos.c, wine: wine-11.21, host_arch: x86_64, without: fail, with: pass, windows: pass, run: https://github.com/unxed/fix-it-in-wine/actions/runs/42156695927}
license: LGPL-2.1-or-later
authors: [T_Im]
---

# winehq-59609: LVM_GETITEMPOSITION in icon views

## Symptom

FastStone Image Viewer (`FSViewer.exe`) shows its full-screen thumbnail strip
with blank spaces instead of thumbnails.

## Cause

In the ICON and SMALLICON views of a list-view, `LVM_GETITEMPOSITION` returns
client coordinates. The Microsoft documentation specifies view coordinates:
the position must not change when the list-view scrolls. FastStone subtracts
the scroll offset from the returned position a second time, concludes that the
thumbnails of the strip are outside the visible area and does not draw them.

## Fix

The fix is in the ticket (comment 0, reporter T_Im): `LVM_GETITEMPOSITION`
returns view coordinates in the ICON and SMALLICON views. The catalog entry
points to the patch as a unified diff against wine-11.0. The `wine` field lists
the tags it is known to apply to: wine-9.0 and wine-11.0.

The patch changes comctl32. A Wine 11 prefix has two modules that contain the
list-view: `comctl32` (common controls version 5) and `comctl32_v6` (version 6,
a separate module from Wine 11 on; earlier releases have no `comctl32_v6`).
Which of them the program loads depends on whether its manifest requests common
controls 6, so both are listed in `dlls`.

## How to apply

One step, for FastStone only: `scripts/apply-winehq-59609.sh` in this repository. It finds
`FSViewer.exe` in `WINEPREFIX`, picks comctl32 v5 or v6 (on Wine 11 the v6 module is
`comctl32_v6`, read from the export name of the file it replaces), downloads the DLL for the
exact `wine --version` from the [release](https://github.com/unxed/dllmgr/releases/tag/winehq-59609)
(checked against SHA256SUMS), and enables it for `FSViewer.exe` only.
`scripts/undo-winehq-59609.sh` restores the DLL and the previous registry value;
`apply-winehq-59609.sh --undo` is also supported. Use the same `WINEPREFIX` for both.
The release is built by `.github/workflows/release-winehq-59609.yml`.
Download failures leave the prefix unchanged; retry later or explicitly pass `--build`
to compile locally. Wine registry output is decoded using the OEM code page for
`LC_ALL`, `LC_CTYPE` or `LANG`, following [localecp](https://github.com/unxed/localecp).

To build the module yourself, apply the patch to the Wine source of your
release and run `tools/build_one_dll.sh <tag> comctl32 [comctl32_v6]` from
fix-it-in-wine.

## Status

Pending. The showcase workflow linked in `evidence` runs the reproducer on
real Windows, on Wine 9.0 without the fix and on Wine 9.0 with the fix. Until
that workflow is green the entry makes no claim about results. The `binaries`
release is optional; the source of truth is the patch and its sha256.
