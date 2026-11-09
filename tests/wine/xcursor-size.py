#!/usr/bin/env python3
"""Print the current X cursor image size, hotspot and name (XFixes)."""
import ctypes
x = ctypes.CDLL('libX11.so.6'); xf = ctypes.CDLL('libXfixes.so.3')
x.XOpenDisplay.restype = ctypes.c_void_p; x.XOpenDisplay.argtypes = [ctypes.c_char_p]
class Img(ctypes.Structure):
    _fields_ = [('x', ctypes.c_short), ('y', ctypes.c_short), ('width', ctypes.c_ushort), ('height', ctypes.c_ushort),
                ('xhot', ctypes.c_ushort), ('yhot', ctypes.c_ushort), ('serial', ctypes.c_ulong),
                ('pixels', ctypes.POINTER(ctypes.c_ulong)), ('atom', ctypes.c_ulong), ('name', ctypes.c_char_p)]
xf.XFixesGetCursorImage.restype = ctypes.POINTER(Img); xf.XFixesGetCursorImage.argtypes = [ctypes.c_void_p]
d = x.XOpenDisplay(None); i = xf.XFixesGetCursorImage(d).contents
# visible extent: bounding box of non-transparent pixels
xs = [k % i.width for k in range(i.width * i.height) if (i.pixels[k] >> 24) & 0xff]
ys = [k // i.width for k in range(i.width * i.height) if (i.pixels[k] >> 24) & 0xff]
box = f"{max(xs)-min(xs)+1}x{max(ys)-min(ys)+1}" if xs else "empty"
print(f"cursor {i.width}x{i.height} visible {box} hot {i.xhot},{i.yhot} name {i.name}")
