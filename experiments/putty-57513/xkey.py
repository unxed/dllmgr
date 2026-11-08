#!/usr/bin/env python3
"""Physical-keyboard emulation for the stand: `xkey.py group N` locks XKB group
N (0 = us, 1 = ru with layout us,ru); `xkey.py keys 24 25 ...` presses keycodes
through XTest (like a real keyboard, no keysym remapping)."""
import ctypes, sys, time
x = ctypes.CDLL('libX11.so.6'); xt = ctypes.CDLL('libXtst.so.6')
x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
d = x.XOpenDisplay(None)
x.XkbLockGroup.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
x.XFlush.argtypes = x.XSync.argtypes = [ctypes.c_void_p]
if sys.argv[1] == 'group':
    x.XkbLockGroup(d, 0x100, int(sys.argv[2]))  # XkbUseCoreKbd
else:
    for k in sys.argv[2:]:
        xt.XTestFakeKeyEvent(d, int(k), 1, 0); x.XFlush(d); time.sleep(.08)
        xt.XTestFakeKeyEvent(d, int(k), 0, 0); x.XFlush(d); time.sleep(.2)
x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]; x.XSync(d, 0)
