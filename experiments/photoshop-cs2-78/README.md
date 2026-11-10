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
