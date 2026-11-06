---
id: faststone-all
kind: bundle
title: "FastStone Image Viewer: composed application fixes"
programs: [FSViewer.exe]
wine: [wine-11.0]
fixes: [winehq-48872, winehq-48874, winehq-59251, winehq-59609]
---

# FastStone Image Viewer

Compose the listed patches before building each affected module. This is not
sequential installation of different comctl32 binaries, which would overwrite
one another. Keep gdiplus in the same install/undo transaction as comctl32.

This is a candidate selection, not a claim that every FastStone bug is fixed.
See [the audit and acceptance criteria](../../docs/faststone.md), including
[the additional user reports](https://github.com/unxed/dllmgr/issues/8).
The current temporary entry points are `scripts/apply-faststone.sh` and
`scripts/undo-faststone.sh`. The GUI is planned; it has not been implemented.
