#!/usr/bin/env python3
"""xkbgroup.py [N]: lock the XKB group (0 = first layout, 1 = second) on $DISPLAY, print the current one."""
import ctypes, sys
x = ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.restype = ctypes.c_void_p
d = x.XOpenDisplay(None)
if len(sys.argv) > 1:
    x.XkbLockGroup(ctypes.c_void_p(d), 0x100, int(sys.argv[1]))
    x.XSync(ctypes.c_void_p(d), 0)
class State(ctypes.Structure):
    _fields_ = [('group', ctypes.c_ubyte), ('locked_group', ctypes.c_ubyte), ('base_group', ctypes.c_ushort),
                ('latched_group', ctypes.c_ushort), ('mods', ctypes.c_ubyte), ('base_mods', ctypes.c_ubyte),
                ('latched_mods', ctypes.c_ubyte), ('locked_mods', ctypes.c_ubyte), ('compat_state', ctypes.c_ubyte),
                ('grab_mods', ctypes.c_ubyte), ('compat_grab_mods', ctypes.c_ubyte), ('lookup_mods', ctypes.c_ubyte),
                ('compat_lookup_mods', ctypes.c_ubyte), ('ptr_buttons', ctypes.c_ushort)]
s = State()
x.XkbGetState(ctypes.c_void_p(d), 0x100, ctypes.byref(s))
print('group', s.group)
