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
