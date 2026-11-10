# #39: Esc ignored for ~1 s after the image is already visible

State 2026-11-09 (agent claude-cloud-ada0). Scripts use sandbox paths
(/home/claude/work/...): esc.sh MODE (private = `dllmgr run` runtime v3,
stock = /opt/wine-stable with the proxy disabled) presses Esc every 100 ms
from launch and reports when FSViewer.exe exits vs the first image on screen
(xsample, X pixels).

Precondition: the owner's FastStone has "confirm on Esc exit" off. The stand
copy had `ConfirmOnESCExit` True in FSSettings.db (binary Delphi DFM
TProgramSettings; boolean byte right after the name, 0x09 True / 0x08 False);
set to False to match. With it True, Esc opens a confirmation that is
invisible (see the separate issue about the hidden FastStone dialog).

## Results (Wine 11.0, 192 DPI)

| WM | mode | first image ms | exit ms (Esc every 100 ms from start) |
|---|---|---|---|
| Metacity | private | 894-1053 | 2180-2520 |
| Metacity | stock | 679-766 | 2049-2296 |
| Muffin | private | 1508-1722 | 2721-2853 |
| Muffin | stock | 1283 | 2157 |

The window shows the image ~1-1.4 s before Esc works: reproduced.

## Mechanism (WINEDEBUG=+timestamp,+key,+event, Metacity, stock)

- 11-12 Esc presses, only 3 reach Wine (X11DRV_KeyEvent); before that the X
  focus is on the WM's own window (xdotool getwindowfocus), so the keys never
  reach FastStone. Not FastStone being busy, not Wine dropping keys.
- The fullscreen viewer window (hwnd 0x100a6) is mapped at T; the WM sends it
  WM_TAKE_FOCUS only at T+0.54 s; Wine handles it immediately (set_focus),
  FocusIn arrives at T+0.72 s. Earlier the WM offered focus to Delphi's 1x1
  TApplication window (WM_TAKE_FOCUS for 0x1007c at map time).
- The first Esc after FocusIn goes to the viewer; focus then moves to another
  new window (0x70132), the next Esc closes the program.
Open: why the WM offers focus to the viewer so late (focus-stealing
prevention with _NET_WM_USER_TIME, the 1x1 TApplication window holding the
focus offer, or the order Wine maps/sets fullscreen); what Windows does
(expected: the new foreground window is active at once). Next step: log
_NET_WM_USER_TIME / WM_HINTS input / _NET_ACTIVE_WINDOW requests of the
three windows with xprop -spy, then try the cheapest PE-side fix in the
existing proxy (SetForegroundWindow/SetFocus on the viewer when shown) and
measure again.

## Correction (2026-11-09, later the same night): it is not focus, it is the late fullscreen window

Relay of user32 activation calls (stock): FastStone shows the image first in
an early `TForm` (0x100aa) and calls SetFocus/SetForegroundWindow on it, then
SetForegroundWindow(Application.Handle) (zero-size TApplication; that is why
the X focus stays with the WM). The window that handles Esc is a separate
`TFullScreenWindow`, created ~1.9 s after the early form; Esc works exactly
from then on.
Tried and rejected (no measured change, reverted): an IAT hook of
SetForegroundWindow in the proxy that keeps the focused form in front when
the target is the zero-size TApplication window. The early TForm gets focus
with it, but does not react to Esc.
So #39 = the ~1.9 s between the early image form and TFullScreenWindow under
Wine. Next: find what FastStone does in that gap (relay/+loaddll timestamps
on the main thread between the two windows; compare with Windows timing on
the windows-probes runner) — overlaps #22 (startup latency).

## Gap timeline (+loaddll, stock, Metacity) — last data of the session

    5969.331  early TForm (0x100aa) mapped (image visible)
    5969.657  fsplugin05.dll loaded
    5969.850  libsharpyuv.dll, libwebp.dll loaded
              ~1.1 s with no DLL loads (unknown work on the main thread)
    5970.940  TFullScreenWindow mapped (Esc works from here)
    5971.059  gdiplus.dll (builtin) loaded
Next: sample the main thread in the 5969.85-5970.94 gap (relay with
RelayFromInclude=FSViewer.exe limited to kernel32/user32/gdi32 file, registry
and shell calls, or winedbg backtraces every 100 ms) and time the same span
on the Windows runner.

## 2026-11-10: sampling the gap is blocked by tooling

Tried three ways to sample FastStone's main thread in the ~1.1 s gap
(runtime rt-cur3, wow64): `perf` does not run on this sandbox kernel
(linux-tools for 6.18 missing); gdb attach sees only Unix-side frames
without the 32-bit PE stack; `winedbg` attach (stdin "attach 0x20 / bt")
crashes the injected break-in thread with a page fault at 0xffc00d6c in
wow64 32-bit code, so no PE backtrace either. The last one looks like a
Wine wow64 debugger bug (to retest on wine.git master before any report).
Parked until a working sampler exists (#22 needs the same).
