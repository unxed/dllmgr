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
    release: photoshop-cs2-v1
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
dllmgr uninstall photoshop-cs2
dllmgr share photoshop-cs2
```

See [installation and sharing](../../docs/recipes.md). `photoshop-cs2-v1`
composes three Wine core fixes delivered through the private runtime:

- **winehq-60721**: win32u/winex11 window surface fix. Removes the white
  flash on first window show; enables the version.dll prefill proxy to
  shape the Photoshop splash margin as transparent and live.
- **dllmgr-43**: winex11 focus fix. Prevents focus stealing during startup.
- **dllmgr-44**: winex11 cursor scaling fix. Scales custom tool cursors at
  192 DPI (32x32 -> 64x64), matching Windows behavior for DPI-unaware apps.

`dllmgr fix photoshop-cs2` installs the private runtime (release
app-isolation-wine-11.0-v4 or later) and the proxy below in one step.

Additionally, the **version.dll prefill proxy** (built from
`patches/dllmgr-27/prefill.c` with `DLLMGR27_CAPTIONLESS_ONLY` and
`DLLMGR27_ACTIVE_IN_RUNTIME`) is installed next to Photoshop.exe by
`scripts/prefill-proxy.py`. This proxy captures the screen under the splash
window and shapes its margin via `SetWindowRgn`.

All Wine core patches are delivered through the private runtime (see
[application isolation](../../docs/app-isolation.md)). The version.dll proxy
is installed per-application by the fix command.

## Remaining work

- Under the private runtime the splash minimizes with the main window but
  shows a white margin around the card (#43 part 1, in progress).
- Shadow halo around the shaped splash (the soft shadow keeps the background
  of the moment it was painted).
- R6025 pure virtual call when closing an image ([#41](https://github.com/unxed/dllmgr/issues/41)).
- Menu artifacts under compositing WM ([#45](https://github.com/unxed/dllmgr/issues/45), fixed by
  winehq-60721 in the private runtime).
- Installer issues: MSI final dialog texts all "&Finish" (F13), msiexec 0x6a6
  crash (F14), MSI dialogs not DPI-scaled (F11/F12), EULA letter spacing (F9).

See [the audit](../../docs/photoshop-wine-audit.md) for the full list.