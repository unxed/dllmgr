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
