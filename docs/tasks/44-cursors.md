# #44 Tiny custom cursors (Photoshop CS2 at 192 DPI)

State 2026-11-09 (agent claude-cloud-ada0).

## Mechanism

Wine 11 virtualizes DPI-unaware windows (window DPI 96, contents scaled 2x
offscreen to the 192 DPI monitor), but winex11 `create_cursor` builds the X
cursor at the bitmap's own size. A 32x32 app cursor is therefore half the
size Windows shows: Windows scales cursors of DPI-virtualized windows by the
display scale. System cursors mapped to the X theme (`left_ptr` etc.) are
not affected (theme size).

## Fix (patches/dllmgr-44.patch, winex11 mouse.c only)

- Scale = monitor raw DPI / window DPI of the window the cursor is set on
  (never shrinks; DPI-aware windows get 1:1, unchanged).
- Mask (and colour) bitmaps are stretched before conversion, hotspot scaled;
  scaled X cursors are cached in a separate XContext. Assumption: one scale
  per cursor handle (true with one monitor DPI); documented in the code.
- Opt-out: `DLLMGR44_NO_CURSOR_SCALE=1`.

## Verification

tests/wine/cursor-scale.sh (tests/wine/cursor-scale.c) on Xvfb, LogPixels=192:

| runtime | mono (CreateCursor) | colour (CreateIconIndirect, 24x24 opaque) |
|---|---|---|
| without patch | 32x32 hot 15,15 | 32x32, visible 24x24, hot 4,4 |
| dllmgr-44 | 64x64 hot 30,30 | 64x64, visible 48x48, hot 8,8 |
| dllmgr-44 + opt-out | 32x32 hot 15,15 | - |

Photoshop CS2 on the patched runtime: its cursors are created at
`scale 192/96` (WINEDEBUG=+cursor).

## Open points

- Over the image canvas Photoshop CS2 hides the cursor (ShowCursor(FALSE))
  and draws the tool cursor itself; on the stand the X cursor there is a
  fully transparent 32x32 (now 64x64) one. The "+" is drawn into the window
  and is already scaled with the window. If the owner still sees a tiny
  cursor after the runtime update: which tool and where (canvas, palettes,
  dialogs)?
- Inverting (XOR) pixels of colour cursors become transparent in Wine's
  Xcursor path (pre-existing, not touched here).
- Delivery: next runtime release (with dllmgr-43), then the pin in
  scripts/private-runtime.json.

## Owner retest, runtime v5 (2026-11-09 14:19)

Owner: magnifier (zoom), eyedropper and hand cursors are still small; the
others are fine (asked to check the rest on the stand).
Stand, v5 runtime via the trampoline, cursor over the canvas (XFixes):

| tool | X cursor | visible art | hotspot |
|---|---|---|---|
| zoom | 64x64 | 32x32 | 12,12 |
| hand | 64x64 | 32x32 | 14,14 |
| eyedropper | 64x64 | 32x32 | 0,30 |
| brush | 64x64 | 32x32 | 16,14 |
| move | 64x64 | 32x32 | 2,2 |
| lasso, type, marquee | 64x64, empty (Photoshop hides the cursor and draws its own) | - | - |

So on the stand the tool cursors are scaled 2x (16 px art -> 32 px), as
Windows does at 200 %. Open: why the owner still sees them small. Next step:
measure on the owner's machine (tests/wine/xcursor-size.py while the zoom
tool is over the canvas) and compare with his system cursor size.
