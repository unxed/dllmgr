#!/usr/bin/python3 -I
"""alttab-emu.py WINDOW: emulate Cinnamon's Alt+Tab switch on a stand WM.

Muffin alone has no Alt+Tab switcher (Cinnamon's is JavaScript), and
`xdotool key alt+Tab` does nothing there. Cinnamon's switch, as X clients
see it: the shell grabs keyboard and pointer (Main.pushModal) while the
popup is shown, on Alt release activates the chosen window with a user
timestamp (meta_window_activate: raise + focus) and then drops the grab.
Here: grab both on the root, wait, send _NET_ACTIVE_WINDOW (source 2 =
pager/WM-side request, timestamp from the server), wait, ungrab.
"""
import sys
import time
from Xlib import X, display, protocol

d = display.Display()
root = d.screen().root
target = int(sys.argv[1], 0)
hold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

# server timestamp: a property change on our own window
w = root.create_window(0, 0, 1, 1, 0, X.CopyFromParent, event_mask=X.PropertyChangeMask)
a = d.intern_atom('DLLMGR_TS')
w.change_property(a, a, 8, b'x')
d.flush()
while True:
    ev = d.next_event()
    if ev.type == X.PropertyNotify:
        ts = ev.time
        break

kg = root.grab_keyboard(False, X.GrabModeAsync, X.GrabModeAsync, ts)
pg = root.grab_pointer(False, 0, X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE, ts)
d.sync()
print('alttab-emu: grab keyboard %d pointer %d' % (kg, pg))
time.sleep(hold)
net_active = d.intern_atom('_NET_ACTIVE_WINDOW')
ev = protocol.event.ClientMessage(window=d.create_resource_object('window', target),
                                  client_type=net_active, data=(32, [2, ts + int(hold * 1000), 0, 0, 0]))
root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
d.sync()
time.sleep(0.2)
d.ungrab_keyboard(X.CurrentTime)
d.ungrab_pointer(X.CurrentTime)
d.sync()
print('alttab-emu: activated 0x%x' % target)
