#!/usr/bin/env python3
"""retransient.py CHILD PARENT: rewrite WM_TRANSIENT_FOR (WM re-reads it on PropertyNotify)."""
import ctypes, sys
x = ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
x.XSetTransientForHint.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong]
x.XFlush.argtypes = [ctypes.c_void_p]
d = x.XOpenDisplay(None)
x.XSetTransientForHint(d, int(sys.argv[1], 0), int(sys.argv[2], 0)); x.XFlush(d)
