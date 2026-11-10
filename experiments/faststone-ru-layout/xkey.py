#!/usr/bin/env python3
"""xkey.py [-g GROUP] KEY...: press physical keys through XTest on $DISPLAY.

KEY is "mod+mod+KEYCODE" (mods: ctrl, shift, alt), e.g. ctrl+38 = Ctrl+A on
evdev. Unlike xdotool this never touches the XKB group: the key gets whatever
group is locked (-g GROUP locks it first, 0 = first layout, 1 = second), so
"Russian active" can also be the second group of us,ru.
"""
import ctypes, sys, time
x = ctypes.CDLL('libX11.so.6'); t = ctypes.CDLL('libXtst.so.6')
x.XOpenDisplay.restype = ctypes.c_void_p
d = ctypes.c_void_p(x.XOpenDisplay(None))
MODS = {'ctrl': 37, 'shift': 50, 'alt': 64}
args = sys.argv[1:]
if args[:1] == ['-g']:
    x.XkbLockGroup(d, 0x100, int(args[1])); x.XSync(d, 0); args = args[2:]
for key in args:
    parts = key.split('+'); code = int(parts[-1]); mods = [MODS[m] for m in parts[:-1]]
    for m in mods:
        t.XTestFakeKeyEvent(d, m, 1, 0)
    t.XTestFakeKeyEvent(d, code, 1, 0); x.XSync(d, 0); time.sleep(.05)
    t.XTestFakeKeyEvent(d, code, 0, 0)
    for m in reversed(mods):
        t.XTestFakeKeyEvent(d, m, 0, 0)
    x.XSync(d, 0); time.sleep(.15)
