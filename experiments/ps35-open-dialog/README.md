# #35 / Wine 34134: CS2 Open dialog keeps the Adobe dialog width (sandbox)

Stand: stock Wine 11.0, Xvfb 3072x1728 @192 DPI, Metacity `--compositor=none`,
CS2 Tryout via scripts/sandbox-install-cs2.sh. Scenario script:
tests/wine/ps35-open-toggle.sh (File > Open, Use Adobe Dialog, Use OS Dialog).

Reproduced exactly as on the owner's laptop (X sizes): OS 1192x1136 ->
Adobe 1520x1136 (a different window) -> OS (same window as before) 1520x1136.

Who resizes (WINEDEBUG=+win, and +relay limited by RelayInclude to
user32.SetWindowPos/MoveWindow/DeferWindowPos to get return addresses):

- OS dialog hwnd 0x20612 (`#32770` "Open", owner Photoshop main window).
  comdlg32 sizes it 565x421, then 604x602 (logical; Photoshop is DPI-unaware).
- Adobe dialog hwnd 0x20928: created 770x522; then
  `SetWindowPos(0x20928, 465,87, 760x602)` (position and height of the OS
  dialog, width 760) from **versioncueui.dll**; Wine's calc_winpos applies the
  minimum track size and makes it 768x602.
- Switching back: `MoveWindow(0x20612, 465,87, 768,602, FALSE)` from
  **versioncueui.dll** (return address 0x09d866bd, module at 0x09d60000).

So the width growth is Adobe's own explicit resize of the OS dialog to the
Adobe dialog's actual rect; Wine executes what it is asked. The OS width only
grows because the Adobe dialog cannot be narrower than ~760-768 here.
Hypothesis (unproven): on Windows the Adobe dialog's minimum width (from its
WM_GETMINMAXINFO, likely font/DPI dependent) is not larger than the OS
dialog's width, so the round trip keeps the size. Next: log the Adobe
dialog's WM_GETMINMAXINFO answer; compare with Windows only if needed.
Wine 34134 c5 (published earlier) says cause unknown; do not post again
until the minimum-size question is answered.
