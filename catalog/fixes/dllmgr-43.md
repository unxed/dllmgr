---
id: dllmgr-43
kind: fix
bug: https://github.com/unxed/dllmgr/issues/43
title: "winex11: send EWMH activation requests with last user time to prevent focus stealing"
dlls: [winex11, win32u]
programs: [Photoshop.exe]
wine: [wine-11.0]
patch: https://raw.githubusercontent.com/unxed/dllmgr/main/patches/dllmgr-43.patch
patch_sha256: b3c0a94b19c5f49a39bd386a18d12ea1e4ffeb8f89b85e81bcaaa23920bae601
recipe: "private runtime: wine-11.0 + wine-11.0-app-isolation.patch + winehq-60721.patch + dllmgr-43.patch + dllmgr-44.patch"
evidence: https://github.com/unxed/dllmgr/issues/43
results:
  - {check: "splash does not stay on top when main window minimized", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/43"}
  - {check: "startup does not steal focus back from other applications", wine: wine-11.0, host_arch: x86_64, prefix_arch: win64, dpi: 192, without: fail, with: pass, run: "https://github.com/unxed/dllmgr/issues/43"}
license: LGPL-2.1-or-later
ai_assisted: true
---

# dllmgr-43

## Problem

Photoshop CS2 on Wine 11.0 (Cinnamon/Muffin, 192 DPI) has two related
startup UX problems:

1. **Splash z-order**: Minimizing Photoshop's main window during startup does
   not minimize the splash; it stays above other windows and covers them.
2. **Focus stealing**: While Photoshop loads, its window keeps taking the
   focus back: switching to another application (e.g., browser) is undone
   again and again.

Both annoy during the ~minute of startup.

## Windows behavior

(measured) On Windows, the splash window is owned by the main window.
Minimizing the owner minimizes the splash. A background process cannot
steal focus from the foreground window due to foreground lock timeout; its
activation request is ignored or deferred by the window manager.

## The fix, in words

Changes to `dlls/winex11.drv/window.c` and `dlls/winex11.drv/x11drv.h`:

1. **Track process user time**: A new static `process_user_time` is updated
   on any user input in the process's windows (`window_set_user_time` with
   `init=FALSE`) or when the WM activates one of them (handling
   `_NET_ACTIVE_WINDOW` with a valid timestamp). This time represents the
   last moment the user was actively interacting with this Wine process.

2. **Activation requests as EWMH application requests**: When Wine requests
   window activation via `_NET_ACTIVE_WINDOW` (in `X11DRV_SetActiveWindow`),
   it now sends the last user time as the timestamp and sets the source to
   "application" (1) instead of "pager" (2). This allows the window manager
   to apply its focus-stealing prevention: a process the user has switched
   away from must not take the focus back.

3. **Splash z-order**: The same mechanism ensures that the splash window
   (which is owned by the main window via `WM_TRANSIENT_FOR` or similar)
   respects the main window's minimized state, so minimizing the main window
   also minimizes the splash.

The patch is part of the private runtime built by CI, which includes:
- `wine-11.0-app-isolation.patch` (application isolation infrastructure)
- `winehq-60721.patch` (window surface fix for #27)
- `dllmgr-43.patch` (focus stealing fix)
- `dllmgr-44.patch` (cursor scaling fix)

## Results

Owner's stack: Cinnamon, X11, Muffin (compositing WM). Stand: Wine 11.0,
Xvfb 3072x1728 @192 DPI, Metacity and Muffin. Both issues resolved on the
private runtime; these are Wine core changes requiring the patched runtime.

See [#43](https://github.com/unxed/dllmgr/issues/43) for the full investigation.