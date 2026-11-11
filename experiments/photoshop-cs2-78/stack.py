#!/usr/bin/python3 -I
"""stack.py: mapped children of the X root, top of the stack first, with
override-redirect flag, geometry and the class/name of the window or of
the client inside a WM frame; then _NET_ACTIVE_WINDOW and the focus."""
from Xlib import X, display

d = display.Display()
root = d.screen().root


def label(w):
    try:
        cls = w.get_wm_class()
        name = w.get_wm_name()
    except Exception:
        return None
    if cls or name:
        return '%s "%s"' % (cls[1] if cls else '-', name or '')
    try:
        for c in w.query_tree().children:
            s = label(c)
            if s:
                return 'frame of 0x%x %s' % (c.id, s)
    except Exception:
        pass
    return None


for w in reversed(root.query_tree().children):
    try:
        a = w.get_attributes()
        if a.map_state != X.IsViewable:
            continue
        g = w.get_geometry()
    except Exception:
        continue
    print('0x%08x %s %5d,%-5d %5dx%-5d %s' % (w.id, 'OR' if a.override_redirect else '  ',
                                            g.x, g.y, g.width, g.height, label(w) or ''))
act = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), X.AnyPropertyType)
print('active', hex(act.value[0]) if act else None, 'focus', d.get_input_focus().focus)
