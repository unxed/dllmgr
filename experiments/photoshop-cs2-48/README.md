# #48 Alt+click does not reach Photoshop under Cinnamon

Cause: Cinnamon's window manager (Muffin) moves windows on Alt+drag
(`org.cinnamon.desktop.wm.preferences mouse-button-modifier = '<Alt>'`, the
default) and takes every Alt+click itself. Photoshop never gets it (Zoom out,
Eyedropper sampling, Clone source...). On Windows, Alt+click belongs to the
application. Under Metacity with `<Super>`, Alt+click with the Zoom tool zooms
out (200 % -> 100 %).

Fix (scripts/private-app.py, setting `alt-click`, Photoshop default `app`):
at launch, if the Cinnamon modifier is exactly `<Alt>`, set it to `<Super>`
and start a detached `private-app.py wm-restore PID`. It waits for the
launching process and then for the prefix's wineserver (`wineserver -w`), and
restores `<Alt>` only if the value is still `<Super>`, so a user's own change
in the meantime is kept. The restore is verified by reading the value back.
The mark file `.dllmgr/wm-modifier` keeps the original value, so a lost
restorer (logout, kill) is redone at the next start. Other desktops (no
Cinnamon schema) and other modifier values are left alone.
`dllmgr set photoshop-cs2 alt-click=desktop` keeps Alt for the window manager.

Checks (2026-11-09, sandbox):
- live.sh: Muffin with the dconf backend; xev gets 0 Alt+clicks with
  `<Alt>`, 1 after a live switch to `<Super>` (Muffin applies it immediately).
- flow.sh: real gsettings/dconf, a real Wine client as the "application":
  `<Super>` while it runs, `<Alt>` again after its wineserver exits; the log
  says "window modifier restored to <Alt>".
- Unit tests: scripts/tests/test_private_app.py AltClickTest.
