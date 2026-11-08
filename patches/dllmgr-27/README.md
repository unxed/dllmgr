# dllmgr-27: FastStone first-open white flash, PE-side workaround

Works on **stock** Wine: nothing in Wine is replaced. A proxy `msimg32.dll`
(FastStone 8.5 imports only `AlphaBlend` from it) forwards all exports to
gdi32 exactly like Wine's msimg32 and, on load, replaces `user32!ShowWindow`
in the exe's import table: a hidden top-level window is shown with the screen
under it pre-presented (copy before ShowWindow, draw + GdiFlush right after),
like Windows keeps the old screen until the app paints.

Install for one app: `msimg32.dll` next to the exe + load order
`msimg32=n,b` for that exe (dllmgr AppDefaults rule). `DLLMGR27_OFF=1`
disables the hook at runtime. Build: `sh build.sh [out.dll]` (i686 mingw).

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
