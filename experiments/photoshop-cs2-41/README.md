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

assert-stack.sh (gdb attached to the 32-bit Wine process, breakpoint on the
throw, stack scanned for return addresses after calls): chain
0xd05c1b -> 0x10f2fe0 -> ... -> 0x10742d0 -> 0x1073f40 -> 0x1078be0 (assert),
called at 0x1074175 with a font reference that is NULL: the caller looks it
up through a CoolType function pointer (Photoshop .data 0x14c6c3c ->
CoolType.dll RVA 0x114b89, not an export) and stores NULL when the lookup
fails. Not the cause: CoolType font caches (AdobeFnt10.lst removed: still
fails). Live patch (keep the reference instead of storing NULL): still
fails, so the reference itself is already NULL.

## #62 root cause and fix (2026-11-09)

CoolType's fallback fonts are MyriadPro-Regular, Myriad-Roman,
TimesNewRomanPSMT and ArialMT (strings in CoolType.dll). Windows always has
the last two; a Wine prefix has none, so the default text style ("Normal",
"defaultStyle" on the stack) gets a NULL font and Photoshop throws
SLO::ProgrammerException. With fresh preferences the exception is
swallowed; once preferences exist it reaches the top-level handler.
Proof: the same failing start opens the document when the names in the
loaded CoolType.dll are live-patched (gdb) to "WineTahoma".
Fix (dllmgr-27 version.dll, Photoshop build): when CoolType.dll loads, its
fallback names point to LiberationSans / LiberationSerif (Arial / Times
metrics) when present, else Wine's own WineTahoma. DLLMGR62_NO_FONT_FIX=1
turns it off. Stand: start with the old prefs and C:\t46.png opens the
document (fixed-start-with-prefs.png shows the normal trial dialog on top).
