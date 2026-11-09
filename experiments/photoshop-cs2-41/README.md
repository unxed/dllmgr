# #41 / #62 on the stand

close-wm.sh: start Photoshop CS2, wait ~100 s, close the main window via the
window manager (wmctrl -c, the same _NET_CLOSE_WINDOW as Alt+F4 and the
title-bar cross), report whether a runtime-error box is left.

2026-11-09, stock Wine 11.0, Cinnamon/Muffin, 192 DPI:
- No document: Photoshop closes cleanly, no R6025 (#41 not reproduced yet).
- With a document on the command line (C:\t46.png): Photoshop shows
  "Unable to continue because of a hardware or system error" right after
  loading, before any close: #62. SLO::ProgrammerException from
  SLOCoolTypeFont.cpp:1633 (Photoshop.exe 0x01078d08), found with
  WINEDEBUG=+relay,+seh and RelayInclude=_CxxThrowException. Fontconfig
  limited to DejaVu: still fails.

#62 bisect: fresh settings open the file fine; after one normal start and
exit the prefs store the type font "Caladea-Regular" (first family Wine
registers in HKLM Fonts) and the next start with a file hits the assert.
The old Prefs.psp alone reproduces it. Not the cause: font smoothing
registry values, the version.dll proxy, fontconfig restriction (Wine keeps
its own registration, so that step was not clean).

More: stored font file in C:\windows\Fonts: still fails; type font switched to
Carlito-Regular in the prefs: still fails. The font name is probably not
the trigger; something else in the prefs written at a normal exit is.
