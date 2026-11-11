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

## Sampling profiler (DLLMGR_SAMPLE)

`DLLMGR_SAMPLE=ms[,seconds]` (default 10 ms, 10 s; works with
DLLMGR27_OFF=1 too): a thread in the proxy suspends the main thread every
`ms`, records EIP and 5 frames of the EBP chain, and after `seconds` writes
`%TEMP%\dllmgr-sample-<pid>.txt` ("ms frame0 frame1 ..." as module+offset).
`DLLMGR_SAMPLE=ms,seconds,go` starts when Z:\tmp\dllmgr-sample-go appears
(touch it at the moment of interest); `DLLMGR_SAMPLE_ALL=1` samples every
thread (lines "ms tTID[m] frames", m = main thread).
Made because perf (sandbox kernel), gdb (no PE frames) and winedbg attach
(crashes under wow64) cannot sample a 32-bit app here. Summary with Wine
syscall names: `tools/sample-report.py FILE [WINE_LIB/i386-windows] [--from MS --to MS]`.

## Crash report (#76, DLLMGR76_OFF=1 turns it off)

A module load/unload log (LdrRegisterDllNotification, last 96 events) and
a vectored exception handler: on an access violation raised in the main
executable it writes `dllmgr76:` lines to stderr (the run log): fault
address and memory state, the module the address lay in if it was loaded
or UNLOADED earlier, the last 12 module events and the recent window events
of #71. Logging only (the exception goes on), at most 4 reports.
`dllmgr run` shows the module in the verdict. Check: tests/wine/crash76.c
(reads from msimg32.dll after FreeLibrary) gives "0x7a4e1000 is inside
msimg32.dll UNLOADED 0 ms ago".

## Hit-test guard (#76, DLLMGR76_NO_GUARD=1 turns it off)

version.dll build only, only for Photoshop.exe 9.0 (link stamp
0x42400fac), also with DLLMGR27_OFF=1. Photoshop's cursor hit test
(exe+0xb01a90) leaves its out window record unwritten when the window under
the cursor (or its owner) has no child with id 0, and one caller then crashes
at exe+0xb249ce (experiments/photoshop-cs2-76/README.md). The exe's
delay-import slot of GetDlgItem is hooked; for a NULL GetDlgItem(.., 0) made
through that slot from the hit test, the record is set to NULL and the hit
test returns 0 ("nothing here") through a small stub. One
`dllmgr76: guard: hit test from exe+0x.. on HWND (class .., parent/owner ..)`
line per window in the run log; `DLLMGR76_TRACE=N` logs the first N such
calls. Clean-room implementation from the description (2026-11-11).

## FastStone "Association Settings" (#73, DLLMGR73_ASSOC)

FastStone's button calls ShellExecuteA("open", "control", "/name
Microsoft.DefaultPrograms /page pageDefaultProgram") (+relay trace), which
does nothing in Wine. When `dllmgr run faststone` sets DLLMGR73_ASSOC (a Unix
command line: `'<dllmgr>' assoc faststone dialog`), the msimg32 proxy hooks
the exe's ShellExecuteA import and runs that command through Z:\bin\sh
instead. Stand check: the button ran the command (a marker file appeared).
`dllmgr assoc faststone dialog` shows a zenity checklist of the file types;
checked types get FastStone as the default, unchecked ones get their
previous default back.

## Message timeline (#47, DLLMGR_MSGLOG=seconds)

A WH_GETMESSAGE hook per hooked thread records every message removed from
the queue (time in 0.1 ms, thread, message, window, wParam) from the moment
%TEMP%\dllmgr-msglog-go exists, for `seconds`; then writes
%TEMP%\dllmgr-msglog-<pid>.txt. Same proxy on Wine and on Windows, to
compare when Photoshop's paint timer fires. Not yet verified end to end
(the first build imported libgcc_s for a 64-bit division and broke the
proxy; fixed with double arithmetic, and build.sh now refuses MinGW runtime
DLL imports).
