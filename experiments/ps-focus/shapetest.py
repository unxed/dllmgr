#!/usr/bin/env python3
"""shapetest.py before|after: white 400x300 managed window, bounding shape 200x150 set before or after map."""
import ctypes, sys, time, subprocess
x = ctypes.CDLL('libX11.so.6'); xe = ctypes.CDLL('libXext.so.6')
x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
x.XDefaultRootWindow.restype = ctypes.c_ulong; x.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
x.XCreateSimpleWindow.restype = ctypes.c_ulong
x.XCreateSimpleWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong]
for f in ('XMapWindow', 'XFlush', 'XSync'): getattr(x, f).argtypes = [ctypes.c_void_p] + ([ctypes.c_ulong] if f == 'XMapWindow' else ([ctypes.c_int] if f == 'XSync' else []))
class R(ctypes.Structure): _fields_ = [('x', ctypes.c_short), ('y', ctypes.c_short), ('w', ctypes.c_ushort), ('h', ctypes.c_ushort)]
xe.XShapeCombineRectangles.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(R), ctypes.c_int, ctypes.c_int, ctypes.c_int]
d = x.XOpenDisplay(None)
w = x.XCreateSimpleWindow(d, x.XDefaultRootWindow(d), 300, 300, 400, 300, 0, 0, 0xff0000)
x.XInternAtom.restype = ctypes.c_ulong; x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
mwm = x.XInternAtom(d, b'_MOTIF_WM_HINTS', 0)
hints = (ctypes.c_long * 5)(2, 0, 0, 0, 0)
x.XChangeProperty(d, w, mwm, mwm, 32, 0, hints, 5)
shape = lambda: xe.XShapeCombineRectangles(d, w, 0, 0, 0, ctypes.byref(R(0, 0, 200, 150)), 1, 0, 0)
if sys.argv[1] == 'before': shape()
x.XMapWindow(d, w); x.XSync(d, 0); time.sleep(1.5)
if sys.argv[1] == 'after': shape(); x.XSync(d, 0)
time.sleep(1.5)
subprocess.run(['import', '-window', 'root', '-crop', '900x800+0+0', '-resize', '30%', '/home/claude/work/cur/shape-' + sys.argv[1] + '.png'])
