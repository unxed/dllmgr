---
id: faststone-all
kind: bundle
application: faststone
profiles:
  - version: "8.5"
    exe_sha256: 05c877e57b25c37e75b8c2a07a5f0ecc31e3b1bb8d12aeb9554c93dcde4ce621
    wine: wine-11.0
    host_arch: x86_64
    prefix_arch: win64
    release: faststone-v2
title: "FastStone Image Viewer: composed application fixes"
programs: [FSViewer.exe]
wine: [wine-11.0]
fixes: [winehq-48872, winehq-48874, winehq-59251, winehq-59609, dllmgr-14]
---

# FastStone Image Viewer

Compose the listed patches before building each affected module. This is not
sequential installation of different comctl32 binaries, which would overwrite
one another. Keep gdiplus in the same install/undo transaction as comctl32.

The preview profile applies to official **FastStone 8.5 x86** in a 64-bit
prefix under **Wine 11.0 on x86-64 Linux**. The official installer and
portable archive contain byte-identical executables. dllmgr recognizes that
executable by SHA256 anywhere under the prefix's C drive. Use
`--exe /path/to/FSViewer.exe` for a portable copy outside the prefix.

```sh
dllmgr fix faststone
dllmgr uninstall faststone
dllmgr share faststone
```

See [installation and sharing](../../docs/recipes.md). The profile restores
missing names under the browser thumbnails in the 192 DPI app comparison.
The four-patch build passed the native controls and GDI+ tests. The profile
still has open app-specific issues including tile overflow, path-field
repainting, fonts and performance. See [the audit](../../docs/faststone.md)
and [the remaining reports](https://github.com/unxed/dllmgr/issues/8).

After applying or undoing a selection, close all Wine applications in the
target prefix and wait for its Wine server to exit before relaunching FastStone.
Wine 11 can keep the previous system DLL mapped in a KnownDLL section for the
lifetime of that server.
