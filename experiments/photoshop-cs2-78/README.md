# #78: palettes stay on screen after switching windows

Stand 2026-11-10 (:96, Muffin, rt-cur3 = v18 + local changes, t78.sh):
Photoshop with a document, a 3000x1650 xclock, Photoshop activated, then
`wmctrl -a xclock` (WM-mediated activation, like a click or Alt+Tab):
xclock goes on top, all Photoshop windows (main, palettes = transients of
the main window, document) below it; screenshot shows only the clock. Not
reproduced. (xdotool alt+Tab does not trigger Muffin's switcher on Xvfb.)

Detail in the owner's screenshots: after the switch the toolbox is drawn
at a different place (x 165-245, y 195-770 in the screenshot) than before
(x 10-95, y 115-690); the right-hand palettes are where they were. Open
questions for the owner: were the stuck palettes clickable (real windows)
or just a picture that went away when Chrome repainted? Which keys
(Alt+Tab, Super, a workspace switch)?

## Update 2026-11-10 18:45: reproduced

With the owner's recipe (click a row in the History palette first, then
switch), t78.sh reproduces it: after `wmctrl -a xclock` the History
palette stays drawn on top of xclock (`t78b-after-switch-25pct.png`);
the other palettes disappear behind or under xclock as expected.

`t78b-xtree.txt` (root children, top of the stack first): the palettes
(0x16000xx, class photoshop.exe) are direct children of the root, not
reparented by Muffin, i.e. Wine keeps them unmanaged (override-redirect).
The History palette 0x1600069 is the topmost window, above the xclock frame
0x400116; the other palettes are below it.

Working hypothesis (to be checked with t78m.sh, which also dumps map states
before and after the switch and runs with WDBG=+event):
- Photoshop hides its floating palettes when the app deactivates and shows
  them again on activation (they are not visible under xclock at all);
- the clicked palette becomes the Win32 active window (the same thing makes
  Alt+F4 close the palette, #82), so it is skipped by that hide pass or is
  re-shown, and as an unmanaged X window it was raised with
  `XConfigureWindow(Above)` by sync_window_position, which nothing undoes;
- a click into it re-activates Photoshop (owner: "brings the whole
  Photoshop back and does nothing else").

## 19:05: map states and the first fix attempt

- t78m.sh (t78c): after the switch all palettes stay mapped (IsViewable);
  Photoshop does not hide them. The event trace: ButtonPress on the History
  palette, FocusOut on the main frame, FocusIn on the palette (the palette
  takes the X input focus, i.e. it becomes the active Win32 window -> #82),
  then FocusOut on the palette when xclock is activated.
- Attempt 1 (local only, not shipped): in winex11 focus_out, when the X focus
  left the process, restack every mapped unmanaged owned popup right above
  its owner's WM frame (XConfigureWindow, CWSibling|CWStackMode Above).
  Result: no change, History still above xclock (t78d). Not yet known
  whether the code ran (no trace), or whether Muffin restacked afterwards.

## 2026-11-10 19:35: Windows reference (CI run 42874590228)

`ps35-windows` measure with `only=palette` (tests/wine/ps35-palette.ps1,
public APIs only; windows-palette.json, windows-after-click.png):
- Palettes are top-level `PSFloatC` windows owned by the main window
  (`Photoshop`), style 0x94800011/0x94800111 (WS_POPUP|WS_VISIBLE|
  WS_CLIPSIBLINGS|WS_BORDER|...), exstyle 0x80 = WS_EX_TOOLWINDOW.
- A click into a palette (the 3rd one, list area) raises it to the top of
  the z-order, but foreground, active and focus windows stay exactly as
  before: the main window is active, the focus does not move.
- Alt+F4 right after that click closes Photoshop (the main window is gone).

So on Windows a palette never becomes the active window. On Wine it does
(FocusIn on the palette after the click): that is both #78 (activation
raises the unmanaged palette above everything, set_input_focus) and #82
(Alt+F4 goes to the palette). The fix must keep the palette from becoming
active, not restack it afterwards. tests/wine/fgprobe78.c prints the same
foreground/active/focus data on Wine.

## 2026-11-10 20:40: F26 startup "program error" bisect (owner's laptop stand)

startup-error.sh, runtime v21, each run on a fresh copy of prefix-clean
(Wine Gecko x86 installed), Muffin, :130. The modal "Could not complete
your request because of a program error" comes up right after the trial
dialog, over the opened t46.png (`wine-f26/1-started-25pct.png`), in all
five runs:

| run | change | program error |
|-----|--------|---------------|
| se1 | Gecko installed in the prefix | YES |
| se2 | + EXTRA="LANG=C LC_ALL=C LANGUAGE=C" (host is ru_RU.UTF-8) | YES |
| se3 | WDBG=+seh,+loaddll,+mshtml,+winspool (trace only) | YES |
| se4 | + CUPS_SERVER=/nonexistent (printer stays in the registry) | YES |
| se5 | printer Epson-LQ-850 deleted from the prefix + CUPS hidden: 0 printers | YES |

Ruled out: Gecko (mshtml.dll is never loaded during startup, so the
Welcome Screen is not an HTML page here), the locale, the host's CUPS
printer. The only rare exception in the se3 +seh trace (the rest are
thousands of routine c0000005/e06d7363/80000026) is one handled
INT_DIVIDE_BY_ZERO at 66B52670 in an Adobe licence-cleanup temp DLL
(`Adobelm_Cleanup...\~de2fd8.tmp` at 66B00000), ~2.5 s after the printer
setup (`wine-f26/seh-divzero-excerpt.txt`); probably the licence code's own
check, relevance unknown. Next chunks to bisect: fonts (FONTCONFIG_FILE
with a minimal set), the prefix-creation recipe vs the cloud one
(mscoree/Mono, winetricks bits), the Photoshop settings/Temp dirs, Xvfb
vs cloud display depth. #78/#82 runs (t78p.sh) wait until startup is clean.

## 2026-11-11: what activates the palette, first fix (patches/dllmgr-78.patch)

Trace (v21, +event,+x11drv,+win): the click makes Muffin send WM_TAKE_FOCUS
to the palette; winex11 handle_wm_protocols calls set_focus, which makes it
foreground/active/focus. Wine 11 no longer asks the window (older Wine sent
WM_MOUSEACTIVATE first). Windows asks: Photoshop's palettes answer
MA_NOACTIVATE and stay inactive.

dllmgr-78.patch (winex11): before activating on WM_TAKE_FOCUS a window that
is not the foreground, send WM_MOUSEACTIVATE (HTCLIENT, WM_LBUTTONDOWN);
MA_NOACTIVATE / MA_NOACTIVATEANDEAT keep the current foreground (the X focus
goes back to it). DLLMGR78_OFF=1: Wine 11 behaviour.
Stand (rt-exp, wine-78-fix/): the History palette answers 3 (MA_NOACTIVATE);
after the click foreground/active/focus stay on the main window (as on
Windows); document windows answer MA_ACTIVATE and still activate. Alt+F4
now goes to Photoshop (its "save changes" box comes up) = #82 fixed.
Still open (#78): the palette becomes WS_EX_TOPMOST (exstyle 0x88; Windows
0x80) on Photoshop's SetWindowPos(HWND_TOP, SWP_NOACTIVATE) after the click:
swp_owner_popups places it right after a hidden topmost popup 0x108d0
(1152x648, ex 0x88), and the server makes it topmost. So it stays above
other apps. tests/wine/zorder78.c (simple model) does not reproduce it;
tests/wine/zlist78.c dumps the real z-order.

## 2026-11-11: topmost part, server fix (patches/dllmgr-78.patch, server/window.c)

Photoshop answers its palette's WM_WINDOWPOSCHANGING for HWND_TOP with
"insert after" its hidden topmost tooltip (tooltips_class32 0x108d0), which
sits right above a hidden topmost PSToolTip (owned by main). Wine's server
link_window then makes the palette topmost (the next window is topmost), so
it stays above other apps (#78).
tests/wine/zorder78b.c reproduces it in miniature. Windows (windows-probes
run 42925193669): P stays non-topmost and goes below all topmost windows
(A, B, P, M). Wine v21: A, P(topmost), B, M.
Fix: a non-topmost window inserted after a topmost one goes below all
topmost windows and stays non-topmost (DLLMGR78_OFF=1: Wine's rule).
rt-exp with it: zorder78b prints exactly the Windows order and "no" for
both variants.
Not done yet: the Photoshop stand run with the server fix (t78p-dismiss.sh
with RT=rt-exp: expect exstyle 0x80 after the click and no palette above
xclock), Wine's user32 win.c z-order tests with the change, the build
script entry (tests/wine/app-isolation-build.sh, after dllmgr-77), runtime
v22 (#77 + #78), e2e, comments on #78/#82.

## 2026-11-11: Photoshop stand run with both parts (rt-exp)

t78p-dismiss.sh + zlist78: after the History click foreground/active/focus
stay on the main window and the palette keeps exstyle 0x80; after switching
to xclock the clock covers the palette (no Photoshop window above it);
Alt+F4 brings Photoshop's own close confirmation. Matches the Windows
reference. Runtime package now also ships bin/wineserver (optional overlay
group, base checksum in app-isolation-check.sh).

## 2026-11-12: cause of the owner's v23 report: the trampoline path runs the stock wineserver

Owner (v23): the palettes stay on top after a switch with a normal launch
(menu entry / .desktop / plain `wine Photoshop.exe`), not with `dllmgr run`.
Live :0 (coordinator's read-only watcher, 2026-11-11 22:08/22:09): the two
palettes above the active window had `_NET_WM_STATE_ABOVE` (= WS_EX_TOPMOST
in winex11); on 2026-11-11 night the owner's Photoshop was served by
`/opt/wine-stable/bin/wineserver` (stock; its sha256 differs from the v23
`bin/wineserver`).

Why: a normal launch starts Photoshop.exe with stock Wine, which starts the
stock wineserver for ~/.wine. The version.dll trampoline (patches/dllmgr-27,
prefill.c `trampoline()`) then runs `dllmgr run` and waits on a named event
and the single-instance mutex, which only works through that same server.
private-app.py `launch()` sets WINESERVER to the runtime's, but Wine only
starts a server when none runs for the prefix, so the private Photoshop
connects to the stock one. The client half of #78 (winex11
WM_MOUSEACTIVATE) is there, the server half (server/window.c link_window)
is not: a palette raised after the hidden topmost tooltip becomes topmost.
The same happens under `dllmgr run` whenever any stock-Wine process keeps
the prefix's server alive.

Stand (full Cinnamon on Xvfb :132, real Alt+Tab, document open,
t78r.sh SERVER0=/opt/wine-stable/bin/wineserver, v23 runtime loader):
History click -> palette exstyle 0x88 + `_NET_WM_STATE_ABOVE`, after the
switch it stays above the terminal; toolbox click -> the toolbox too
(2 Photoshop windows above the terminal, as on the owner's :0). The same run
with the runtime's own wineserver: always 0x80, nothing above
(t78d-cinn-key, -keyhold, -wmctrl, -busy, -pal; PAL/BUSY did not find any
other path to 0x88).

Proposed fix (not done): do the #78 z-order rule on the client side, in
win32u (shipped in the overlay, loaded whatever server runs): in
set_window_pos, after WM_WINDOWPOSCHANGING, a window that is not topmost and
is not asked to become topmost, with an insert-after window that is
topmost, gets HWND_TOP instead (the server then puts it on top of the
non-topmost windows = the Windows result of tests/wine/zorder78b.c). Keep
the server part or drop it. Also: `dllmgr run` could log in launch.log
which wineserver binary serves the prefix, and runtime fixes should not
live only in wineserver (trampoline launches never get it).

## 2026-11-12: fix moved to win32u (patches/dllmgr-78.patch), server part dropped

win32u set_window_pos, after WM_WINDOWPOSCHANGING and swp_owner_popups: a
top-level window that is not WS_EX_TOPMOST, with an insert-after window that
is, gets HWND_TOP (the server then puts it on top of the non-topmost windows,
or above its topmost owner). DLLMGR78_OFF=1: Wine's rule. The server hunk is
gone and the runtime no longer ships bin/wineserver; the winex11
WM_MOUSEACTIVATE part is unchanged.

Stand, local build (rt78c = v23 with this win32u.so and a wineserver without
the server hunk):
- tests/wine/zorder78b: A, B, P, M with P not topmost on the runtime server
  and on the stock server (Windows order); DLLMGR78_OFF=1 on the stock server
  gives P topmost (the bug).
- Photoshop, full Cinnamon on :132, document open, SW=key, t78r.sh:
  SERVER0=/opt/wine-stable/bin/wineserver (owner's normal-launch case) and
  the runtime's own server: History click, toolbox click, document click +
  History, document focused: after every Alt+Tab 0 Photoshop windows above
  the terminal, no palette with exstyle 0x88 in any dump
  (out/t78fix-stocksrv, out/t78fix-ownsrv).

CI build (app-isolation run 43126123680, package sha256 3b9960fb…, no
bin/wineserver in it), installed with `dllmgr fix photoshop-cs2
--runtime-package` on a fresh prefix-clean copy:
- t78r.sh TRAMP=1 (the owner's normal launch: /opt/wine-stable/bin/wine
  Photoshop.exe, trampoline -> dllmgr run): the prefix is served by
  /opt/wine-stable/bin/wineserver, Photoshop maps the runtime's win32u.so;
  all scenarios 0 Photoshop windows above the terminal, no exstyle 0x88
  (out/t78fix-tramp-key). launch.log: "starting the private runtime;
  wineserver: already running /opt/wine-stable/bin/wineserver (not the
  runtime's)".
- Original #78 scenario (NODOC=1, SW=wmctrl, rt78c, both servers): History
  click keeps the main window foreground, nothing above after the switch.
- e2e.sh (fresh install, C:\t78.png): handover to the private runtime, the
  document opens (66.7 %, so the script's "@ 100%" grep says NOT OPEN); the
  F26 "program error" box comes up at startup as before on this stand, so
  the ru Ctrl+N step got nothing (F26, unchanged).
