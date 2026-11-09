# #45 Black rectangles while moving through Photoshop CS2 menus

State 2026-11-09 (agent claude-cloud-ada0). Owner's stack: Cinnamon, X11,
Muffin (compositing WM).

## Result: reproduced on the stand, not caused by the prefill proxy, fixed by our runtime

experiments/ps-focus/menu-burst.sh: Photoshop loaded, open File, then hover
File/Edit/Image three times while 40 screenshots are taken; a frame counts
as bad when more than 10 % of the captured area is pure black (the menu
window shown black before its first paint, see the frame in the run dirs).

| WM | Wine | proxy | bad frames |
|---|---|---|---|
| Muffin | stock 11.0 | version.dll (prefill on) | 5/40 |
| Muffin | stock 11.0 | DLLMGR27_OFF=1 | 6/40 |
| Muffin | private runtime (winehq-60721 + dllmgr-43/44) | DLLMGR27_OFF=1 | 0/40 |
| Metacity, no compositor | stock 11.0 | DLLMGR27_OFF=1 | 0/40 (menu did not switch there; weak control) |

Mechanism: the same as #27 / WineHQ 60721 (a new window is mapped before its
surface content is presented; a compositing WM shows the empty pixmap,
black). The runtime's winex11/win32u fix covers menus too.

## Delivery

Photoshop CS2 must run on the private runtime: PS-3 recipe
(`dllmgr fix photoshop-cs2`), which also delivers #43 and #44. WineHQ:
add "menus under a compositing WM" to the 60721 follow-up
(docs/upstream-outbox.md). Not Mint-specific (any compositing WM).

## Owner, 2026-11-09 14:31 (runtime v5): menus still flash black

Stand, PS-3 installed, plain `wine Photoshop.exe` -> trampoline -> runtime with
the version.dll proxy active: 0/40 bad frames; same start with
DLLMGR27_OFF=1 (no trampoline, so stock Wine): 4/40. So either the owner's
Photoshop does not run on the runtime (see 44-cursors.md, same check), or
the black comes from his real-GPU compositing that Xvfb does not reproduce.
