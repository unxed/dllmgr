---
id: photoshop-cs2
kind: bundle
application: photoshop-cs2
profiles:
  - version: "9.0"
    exe_sha256: 98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30
    wine: wine-11.0
    host_arch: x86_64
    prefix_arch: win64
title: "Adobe Photoshop CS2: composed application fixes"
programs: [Photoshop.exe]
wine: [wine-11.0]
fixes: [winehq-60721, dllmgr-43, dllmgr-44]
---

# Adobe Photoshop CS2

Compose the listed fixes into a single application fix set. This bundle
requires the **private runtime** (built by CI) for the Wine core patches
and the **version.dll prefill proxy** (built by CI, installed by
`scripts/prefill-proxy.py`) for the splash fix.

The preview profile applies to official **Photoshop CS2 9.0 Tryout x86** in a
64-bit prefix under **Wine 11.0 on x86-64 Linux**. The official installer is
available at https://download.adobe.com/pub/adobe/photoshop/win/cs2/Photoshop_CS2.exe
(SHA256: 919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea).
dllmgr recognizes the installed executable by SHA256 anywhere under the
prefix's C drive. Use `--exe /path/to/Photoshop.exe` for a portable copy
outside the prefix.

```sh
dllmgr fix photoshop-cs2
dllmgr unfix photoshop-cs2
dllmgr share photoshop-cs2
```

See [installation and sharing](../../docs/recipes.md). The bundle composes
three Wine core fixes, all delivered through the private runtime (there are
no private module DLLs for Photoshop, so this profile has no prebuilt-module
release tag):

- **winehq-60721**: win32u/winex11 window surface fix. Removes the white
  flash on first window show (FastStone) and the black frame under the
  Photoshop menus under a compositing WM (#45).
- **dllmgr-43**: winex11 focus fix. Prevents focus stealing during startup.
- **dllmgr-44**: winex11 cursor scaling fix. Scales custom tool cursors at
  192 DPI (32x32 -> 64x64), matching Windows behavior for DPI-unaware apps.

`dllmgr fix photoshop-cs2` installs the private runtime (release
app-isolation-wine-11.0-v5 or later, pinned in
`scripts/private-runtime.json`) and the proxy below in one step.

Additionally, the **version.dll prefill proxy** (built from
`patches/dllmgr-27/prefill.c` with `DLLMGR27_CAPTIONLESS_ONLY` and
`DLLMGR27_ACTIVE_IN_RUNTIME`) is installed next to Photoshop.exe by
`scripts/prefill-proxy.py`. The proxy adopts the splash as a managed
transient window (so it minimizes with the main window) and shapes it from
the card's own alpha, taken from the `AlphaBlend` call that Photoshop makes
into `msimg32`; nothing is read back from the screen, so no stale pixels
can be captured.

All Wine core patches are delivered through the private runtime (see
[application isolation](../../docs/app-isolation.md)). The version.dll proxy
is installed per-application by the fix command.

Owner check on runtime v5 (2026-11-09): the splash is shaped, minimizes with
the main window, and the halo is nearly gone.

## Remaining work

- The splash's soft shadow is cut (the card is shaped from its own alpha);
  true per-pixel alpha is in progress (#36).
- A thin light rim stays at the left and top edges of the card (pixels with
  128 <= alpha < 255 that Photoshop blends over the white surface).
- R6025 pure virtual call when closing an image ([#41](https://github.com/unxed/dllmgr/issues/41));
  the owner also saw it on Alt+F4.
- The zoom, eyedropper and hand cursors still look small on the owner's
  machine, although the runtime scales them 2x on the stand
  ([docs/tasks/44-cursors.md](../../docs/tasks/44-cursors.md)).
- Menu artifacts under compositing WM ([#45](https://github.com/unxed/dllmgr/issues/45), fixed by
  winehq-60721 in the private runtime).
- Installer issues: MSI final dialog texts all "&Finish" (F13), msiexec 0x6a6
  crash (F14), MSI dialogs not DPI-scaled (F11/F12), EULA letter spacing (F9).

See [the audit](../../docs/photoshop-wine-audit.md) for the full list.