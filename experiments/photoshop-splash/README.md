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
