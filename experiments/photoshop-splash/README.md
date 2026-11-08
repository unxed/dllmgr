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
