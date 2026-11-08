# dllmgr-27: FastStone first-open white flash, PE-side workaround

Works on **stock** Wine: nothing in Wine is replaced. A proxy `msimg32.dll`
(FastStone 8.5 imports only `AlphaBlend` from it) forwards all exports to
gdi32 exactly like Wine's msimg32 and, on load, replaces `user32!ShowWindow`
in the exe's import table: a hidden top-level window is shown with the screen
under it pre-presented (copy before ShowWindow, draw + GdiFlush right after),
like Windows keeps the old screen until the app paints.

Two entry points from the same `prefill.c`: `sh build.sh msimg32` (FastStone
imports it) and `sh build.sh version` (loads before Photoshop CS2's UI
modules; #36). Install / check / undo for one exe:

    sh patches/dllmgr-27/build.sh version /tmp/version.dll
    scripts/prefill-proxy.py apply  --exe ".../Photoshop.exe" --proxy version --dll /tmp/version.dll
    scripts/prefill-proxy.py status --exe ".../Photoshop.exe"
    scripts/prefill-proxy.py undo   --exe ".../Photoshop.exe"

It copies the DLL next to the exe and sets `<dll>=native,builtin` under
AppDefaults for that exe name only (previous value restored on undo; hashes
checked). Hooks are per-thread message hooks (`DLLMGR27_MODE=iat` = old
exe-IAT ShowWindow hook); `DLLMGR27_OFF=1` disables, `DLLMGR27_DEBUG=1`
traces captures. Verified for Photoshop CS2 on stock Wine 11.0: splash
without the white rectangle (#36).

Result on the sandbox stand (stock /opt Wine 11.0, Metacity, 192 DPI,
tests/wine/first-open-x.sh, X-pixel verdict), 3 runs each:

| | after the first image |
|---|---|
| stock | black ~20 ms -> **white 75-170 ms** -> image |
| stock + dllmgr-27 | black 21-28 ms -> image (no white) |
| Wine patched with winehq-60721.patch | no interruption |

The remaining 1-2 frame black is the X window background before the first
flush; only the Wine-side patch removes it. Notes: the first proxy build
crashed the loader (Delphi images have no OriginalFirstThunk; slots are found
by resolved address now). Only `ShowWindow` is hooked; windows shown via
`SetWindowPos(SWP_SHOWWINDOW)` are not covered yet.

## Trampoline (every launch path, 2026-11-09)

If a companion file `<proxy name>.dllmgr` (e.g. `msimg32.dllmgr`) lies next
to the proxy, a stock-Wine start of the exe relaunches itself through the
private runtime before its first window exists. The file has one UTF-8 line:
a Windows command-line prefix whose first token is the double-quoted
launcher, e.g. `"Z:\home\u\dllmgr\dllmgr" run faststone --`; the exe's own
arguments are appended. The stock process waits for the named event
`dllmgr27-trampoline`, which the proxy sets when it loads inside the private
runtime (DLLMGR_TARGET_EXE in the environment; the proxy is otherwise idle
there), then exits. No signal within `DLLMGR27_TRAMP_WAIT` ms (default
15000) or launcher not startable: it stays on stock Wine with the prefill
backstop. `DLLMGR27_NO_TRAMPOLINE=1` disables only the trampoline.
Test: tests/wine/trampoline-e2e.sh. Design and measurements:
docs/tasks/27-every-launch-path.md.
