# #40: Esc exit confirmation behind the fullscreen viewer

2026-11-10, stand (Muffin, 3072x1728, 192 DPI), fresh prefix, FastStone 8.5
copy with ConfirmOnESCExit=True, started with an image (fullscreen viewer),
Esc after 12 s (t40.sh OUT RT): the confirmation "FastStone" is on top of
the fullscreen window and focused, both with stock /opt/wine-stable and
with the local runtime (incl. #68). Not reproduced
(stock-wine-dialog-visible.png). The original observation (2026-11-09) was
on the private runtime v3 era, Metacity and Muffin; the #68 mechanism (an
activated window without _NET_WM_USER_TIME stacked below the focused one)
would explain it when the viewer holds a newer user time.
