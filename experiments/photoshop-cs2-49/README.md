# #49 Photoshop CS2 shortcuts with the Russian layout

Stand :95 (Cinnamon/Muffin), `hotkey.sh START_GROUP PRESS_GROUP [RUNTIME]`
with LAYOUT=us,ru|ru,us; keys are sent as keycodes (physical keys), Ctrl+N
must open "New", KEY=56 (B) must change the tool options bar; TYPE=1 types
the N key into the New dialog. Use LC_ALL=C.UTF-8 (the stand has no
other UTF-8 locale; with C the Cyrillic characters cannot be produced at all,
stock Wine included). xkbgroup.py locks an XKB group, but xdotool resets
the group of its own events, so "press in the second group" cannot be
injected this way; ru,us (Russian first) exercises the Cyrillic group.

Findings (2026-11-09, stock Wine 11.0):
- us,ru: Ctrl+N and B work (Photoshop builds its shortcut map at start
  from group 0 = Latin).
- ru,us: Ctrl+N does nothing. +relay: Photoshop maps shortcut letters with
  ToUnicodeEx(vk, ..., hkl 0x04090409) (US layout, explicitly). Wine ignores
  the hkl and answers from the X group of the last key event (group 0 =
  Russian at start), so no key maps to 'n'. Also Wine's layout detection
  fails for Russian in a UTF-8 locale (3 matches of 51) and leaves arbitrary
  0x60+ scancodes on letter keys (Ctrl+N had scan 0x7d instead of 0x31).

dllmgr-49 (runtime, winex11 + win32u):
1. evdev keyboards: keycodes 9..96 get their physical scancode (keycode-8).
2. The reported keyboard layout follows the active XKB group (Cyrillic group
   -> 0x04190419, else the locale's); win32u accepts it from the driver.
3. ToUnicodeEx with the US layout while the X group is Cyrillic answers from
   the US table (Windows behaviour for an explicit hkl).
Text input keeps Cyrillic: TranslateMessage passes the reported (Russian)
layout. Switches: DLLMGR49_NO_EVDEV_SCAN, DLLMGR49_NO_LAYOUT_TRACKING.

Stand with the local runtime (ru,us, LC_ALL=C.UTF-8): Ctrl+N opens New, B
selects the brush, typing the N key in the dialog gives WM_CHAR U+0442 "т".
