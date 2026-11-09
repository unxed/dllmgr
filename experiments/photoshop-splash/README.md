# #36 Photoshop CS2 splash: white rectangle (sandbox notes)

2026-11-08, sandbox stand (Wine 11.0, Xvfb 3072x1728 @192 DPI, Metacity
`--compositor=none`), CS2 Tryout installed by scripts/sandbox-install-cs2.sh
into a fresh prefix; captures via tests/wine/ps-splash-shots.sh.

- Reproduced: the splash has an opaque white rectangle around its rounded,
  shadowed card, drawn over the grey main window.
- Negative result: the #27 research build in mode 2 + X background None
  (experiments/first-open/exp27-expose-background) leaves the white rectangle
  unchanged. So the white is pixels Photoshop itself paints from whatever it
  read as "background", not Wine flushing an unpainted surface.
- Hypothesis to test next (not proven): Photoshop captures the screen under
  the splash through a screen DC; Wine's screen-DC reads can return Wine's own
  surface contents instead of what X shows (docs/sandbox-findings.md F18), and
  a fresh surface is 0xff white. Check with a synthetic test: window shown but
  unpainted / hidden, then BitBlt from the screen DC under it, compare with X.
  Wine #34133 c3 (Alexandre) and #10091 point at reading existing pixels.

## Window facts and refined hypothesis (2026-11-08 19:20)

`tests/wine/winstyles.c` during startup: the splash is a plain top-level
`PSFloatC` window, style `94000200`, ex-style `00000101`, **not layered, no
window region**; the main `Photoshop` window is shown before it. So the
"transparency" is drawn by Photoshop itself.

`tests/wine/screen-read-under.c` (screen-DC BitBlt under a shown, unpainted
window): stock `ffffff`, stock + dllmgr-27 prefill `f0cc5a`, Wine with
patches/winehq-60721.patch `f0cc5a`. Yet the real splash stays white on the
winehq-60721 build too, so Photoshop does not take that path.

Refined hypothesis (unproven): Photoshop alpha-blends the rounded card and
shadow onto the existing contents of its **own** splash window. On Windows
without DWM a new window initially shows the screen under it; in Wine the
window surface starts as 0xff, hence white (old Wine: black, matching the
original #34133 report). Candidate PE-side fix: the dllmgr-27 prefill (draw
the screen under a new top-level window into it right after it is shown)
applied inside Photoshop. Photoshop.exe imports only kernel32/msvcr71/msvcp71,
so an exe IAT hook is not enough: use WH_CALLWNDPROC(RET) hooks
(WM_SHOWWINDOW -> capture, WM_WINDOWPOSCHANGED+SWP_SHOWWINDOW -> draw) from a
DLL loaded into the process.

## Confirmed: prefill fixes the splash (2026-11-08 19:35)

The msimg32 proxy loads too late in Photoshop (after its windows are shown;
DLLMGR27_DEBUG showed the hook thread but no captures). A `version.dll` proxy
built from the same `patches/dllmgr-27/prefill.c` (`sh build.sh version`;
exports forward to kernelbase/kernel32, VerInstallFileA/W stubbed) loads before
Photoshop.dll. On **stock** Wine 11.0 with `version=n,b` for Photoshop.exe:

    dllmgr27: capture ... class=Photoshop flags=0043 / present
    dllmgr27: capture ... class=PSFloatC  flags=0057 / present   (x2)

and the splash shows **no white rectangle**: its margin and shadow are drawn
over the grey main window. So Photoshop composes the splash over the existing
contents of its own window, which on Wine was the 0xff initial surface.
Screenshots kept local (they show the registered user name).
Next: package this as an app-scoped dllmgr fix for Photoshop.exe; then check
the splash over other backgrounds and that later dialogs/palettes look normal.

## DPI fix and full-UI check (2026-11-08 19:35)

First full-startup check with the proxy showed a regression: a small,
not-yet-painted window at the top left displayed a 2x enlarged copy of the
menu bar. Photoshop is DPI-unaware and Wine scales its coordinates, while the
capture was logical and the window DC scaled. The proxy now captures and draws
in physical pixels (SetThreadDpiAwarenessContext per-monitor around both,
WINDOWPOS moves/sizes converted with the real screen DPI). Re-run (stock Wine,
192 DPI): splash without white, no enlarged copies, final UI (toolbox, options
bar, palettes) normal. Remaining observation: a faint light 1 px line along the
right/bottom edge of the splash window rectangle (probably its own frame,
previously hidden by the white fill); not compared with Windows yet.

## Owner retest with the version.dll prefill proxy (2026-11-09, owner's laptop)

Better than stock (no white frame), but not finished. Screenshots (cropped to
the splash) in owner-2026-11-09/:
1. Over the main window: the frame around the splash shows the grey captured
   background, but a thin 1 px outline of the splash rectangle stays visible
   (also listed as the #36 leftover). A second, lower window (about 620x37
   under the splash, x 689-1311) is shown white with a line in it: another
   window whose first paint is white (see the correction below: it is the
   owner's screenshot tool).
2. Main window minimized while the splash is up: the frame is grey (screen
   captured when the main window was still behind it) over the desktop: the
   capture is a static snapshot and goes stale when what is behind changes.
3. Same as 1, "Looking for preferences..." stage.
Owner: "шероховато, дошлифовать бы". Ideas to check (not tried): how Windows
renders this splash (layered window with alpha or colour key? then a fix is
to emulate the layering, not to snapshot); refresh the capture when the
windows behind change; find the 1 px line (window border style vs our
capture offset).

Correction (owner, 2026-11-09 01:47): the lower white window in screenshot 1
is not Photoshop's: it is the owner's screenshot tool, which ends up stacked
between Photoshop's main window and its splash. Not a first-paint issue; open
question only whether that stacking (a foreign window between the main window
and the splash) matches Windows.

## The real defect: the margin is opaque and frozen (owner, 2026-11-09 01:49)

Screenshot 4 (owner enlarged the screenshot tool window on purpose, to show
which window the white strip of screenshot 1 was): the screenshot tool's window opened later between Photoshop's
main window and the splash; the splash's rectangular margin (everything
outside the rounded card, feather and shadow) hides it with the grey snapshot
taken when the splash appeared. The margin should be see-through and live.
The prefill snapshot only fixes the first frame; any change behind the splash
afterwards (window opened, main window minimized) shows the stale copy.

Proposed fix (not tried yet, Opus idea): after Photoshop has composed the
splash over our prefilled snapshot, compare the window contents with the
snapshot: pixels that are byte-identical were never touched by Photoshop,
so they are pure background. Cut them out of the window with SetWindowRgn
(X shape), leaving the card, the feather and the soft shadow. The margin then
becomes truly transparent and live; only the shadow keeps the old background
mixed in (a few pixels wide, hardly visible). Also likely removes the 1 px
outline if it comes from the rectangle edge. Check first how Windows looks
in the same scene (Windows CI): if Windows also freezes the margin, this is
a dllmgr improvement beyond parity, which the owner asked for anyway.

## Shaped splash margin: implemented (2026-11-09, patches/dllmgr-27/prefill.c)

How it works (all public Win32 APIs, in the proxy):
- For a top-level window without caption and without WS_EX_TOOLWINDOW, at
  least 200x100, the prefill capture is kept after it was drawn.
- In the window's own thread (winex11 applies a window region only there;
  Photoshop's main thread does not pump messages while the splash is up and
  paints it directly through GetDC/ReleaseDC), at most every 20 ms the proxy
  compares the window with the capture. Entry points: our message hooks and a
  ReleaseDC hook. Photoshop.exe gets user32 through its **delay-import** table
  (resolved after our DllMain), so that slot is patched directly; normal import
  tables of all modules (also later ones, LdrRegisterDllNotification) too.
- When more than 10 % is painted and the window's outer 1 px ring is mostly
  untouched (a margin reaching the border; palettes and dialogs paint their
  own frame there and are never cut), the pixels still equal to the capture
  are cut out with SetWindowRgn. DLLMGR27_NO_SHAPE=1 disables it.
Things tried and dropped on the way: a thread timer and a window timer (never
dispatched during the splash), a worker thread calling SetWindowRgn (winex11
queues it to the owner thread, applied only after the splash), waiting for two
equal measurements (Photoshop goes quiet after the first paint).

Results on the stand (stock Wine 11.0, Metacity, 192 DPI, prefix-auto):
- Splash with the main window minimized: the margin is see-through (X root
  visible), card, feather and shadow intact; without shaping it stays the
  frozen grey snapshot. Trace: `shape hwnd=... 687x463 painted=82%`, edge 0/2296.
- Full startup (100 s): only the splash is shaped; Navigator/Color/History/
  Layers palettes, toolbox and options bar normal. (A first version without the
  edge/toolwindow tests cut holes into partially painted palettes.)
- FastStone with the same source (msimg32 build): first-open-x 3/3 pass.
Remaining: the soft shadow keeps the background of the moment it was painted
(a few px); before Photoshop paints the card the prefill rectangle is still
shown for a moment (on the stand black, because the main window is not painted
yet when the splash appears; grey on the owner's desktop).

## Owner retest of the shaped splash (2026-11-09 08:29)

Much better (owner). Screenshots 5 and 6: the rectangle is gone, but a grey
ring with rounded corners (~20 px, the soft shadow) stays around the card,
clearly visible over a light browser window (5). Cause: Photoshop composes
the shadow (and the feather's antialiased edge) over its own capture of the
screen behind, taken via GetDC(GetDesktopWindow()) + BitBlt; the result is
opaque pixels with that old background mixed in. Shaping cuts only pixels it
never touched. Proper fix needs per-pixel alpha (layered window): see "alpha
recovery" below when it is designed.

## New: "Adobe Activation" dialog draws with a grey background (screenshot 7)

After startup the trial activation dialog shows the grey of the window behind
it as its background; only the text boxes are filled (white / beige). Owner:
seems to depend on how windows are switched during startup, i.e. on what was
under the dialog when it appeared: the prefill snapshot. Suspected regression
of the prefill proxy (stock Wine would show its white initial surface there).
To check: same dialog with DLLMGR27_OFF=1 and on Windows.

## Activation dialog: fixed by limiting the Photoshop prefill to the splash

Owner A/B (2026-11-09 08:54): with DLLMGR27_OFF=1 the background is a white
rectangle (screenshot 8: stock splash). So the grey activation dialog body was
the prefill snapshot: that dialog never paints its own body. The version.dll
build (Photoshop) is now compiled with DLLMGR27_CAPTIONLESS_ONLY: only windows
without a caption get the prefill (the splash). Stand: splash still shaped,
full UI normal.

## Shadow halo: work in progress (not in main)

experiments/photoshop-splash/wip-shadow-cut-prefill.c keeps the attempt to cut
the shadow too. Findings on the way:
- Photoshop does NOT grab the screen itself: the 687x463 GetDC(NULL)+BitBlt in
  the relay log came from our own capture_under. It composes margin and shadow
  over what its window already holds (our prefill), so the capture is the
  right reference; corner pixels matched exactly (808080/808080).
- Shadow pixels are a pure darkening of that background (R = k * B per
  channel): 263740 changed, 222968 kept after dropping them.
- shape_tick re-entered itself (SetWindowRgn repaint -> ReleaseDC hook): fixed
  with a busy flag in the WIP.
- Open bug in the WIP: with the shadow cut, the card shows only a top band and
  a left strip (black elsewhere) although the dumped window pixels are the full
  card; restoring the pixels with SetDIBitsToDevice after SetWindowRgn did not
  help. Also black text on the card is classified as shadow (k = 0). Needs a
  smarter classification (only pixels outside the card's rounded rectangle,
  e.g. a ring found from the outer edge inwards) and a look at how Wine
  recreates the surface on SetWindowRgn.
