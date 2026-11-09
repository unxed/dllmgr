# Owner test of runtime v5 (2026-11-09 14:12-14:14, Mint Cinnamon, Muffin)

`dllmgr fix photoshop-cs2` with app-isolation-wine-11.0-v5.

1. 1-startup-grey-no-cursor.png: for a few seconds after start the main
   window is empty grey and the mouse cursor is not visible over it (the
   machine was busy at that moment; went away by itself). New observation.
2. 2-splash-alpha-shape.png: splash shaped from its own alpha, minimizes with
   the main window ("космос"). Halo almost gone; a thin light rim remains at
   the left and top edges of the card (pixels with 128 <= alpha < 255 that
   Photoshop blended over the white surface).
3. 3-r6025-on-close.png: "Wine C++ Runtime Library: R6025" when closing
   Photoshop (issue #41).
