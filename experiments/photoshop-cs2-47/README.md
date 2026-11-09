# #47 Zoom redraws in steps (2026-11-09, stand, Muffin)

zoomburst.sh: Zoom tool click on a textured image, 20 screenshots taken as
fast as possible (~70-100 ms apart), canvas area.

Stock Wine (zoom-click-stock.png) and runtime with dllmgr-46
(zoom-click-runtime-46.png) look the same: old picture, then ONE frame where
only the top-left tile of the new zoomed picture is drawn over the old one,
then the full new picture. Photoshop renders the zoomed view tile by tile and
Wine presents each tile as soon as it is drawn. On Windows (DWM) GDI drawing
is composed at the display refresh, so tiles drawn within one refresh appear
together; whether Windows shows the same intermediate tile is not measured.
Alt+wheel not tested yet: the stand's keyboard does not reach Photoshop.
Ideas: present a DPI-scaled window's surface at most once per refresh
(batching the tiles of one repaint), measure on Windows first.
