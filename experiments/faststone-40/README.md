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

## 2026-11-10 19:45: owner's report "Esc does nothing in the first moments" (v20)

Owner's laptop stand (console agent, Muffin, isolated HOME), 6000x4000 JPEG.
- t40b.sh (`dllmgr run faststone -- IMG`, Esc N s after the window maps):
  the confirmation comes at every delay tried (0.3 s, 1 s) when the key
  reaches FastStone at all.
- t40c.sh (timeline every 50 ms, map / X focus / _NET_ACTIVE_WINDOW):
  private runtime v21: FastStone windows mapped at 2.39 s, the X focus
  reaches them only at 3.95 s; stock /opt/wine-stable 11.0: mapped 1.47 s,
  focus 3.20 s. In that 1.5-1.7 s gap the window is on screen but keys go
  to the previously focused window (the owner's terminal), so an early Esc
  is lost. Same with stock Wine: not a runtime regression. Next: what holds
  the activation back (Wine's request vs Muffin's focus policy), and what
  Windows does (a started program is foreground at once).
