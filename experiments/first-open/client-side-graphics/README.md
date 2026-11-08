# Rejected ClientSideGraphics workaround — issue27

2026-11-08, stock Wine11.0, official FastStone8.5, disposable win64 prefix,
192DPI, invisible Xvfb:93/Metacity, synthetic800x600JPEG. The normal user
prefix and its settings were never changed.

Wine supports the per-program value
`HKCU\Software\Wine\AppDefaults\FSViewer.exe\X11 Driver`,
`ClientSideGraphics` (REG_SZ). It was absent before testing. Set to `N` only
in the disposable prefix, then delete the value in a finally block. This setting
is per executable basename, not the exact-path private-DLL mechanism.

- Stock before: image→white→image reproduced.
- N/direct drawing: image1757ms → black centre1775ms → image1937ms. White flag0,
  but a162ms black interruption remains. **Rejected as a fix.**
- Stock restored: image→white→image reproduced again. Registry undo succeeded.

The summary's observed_flash means only the observer's explicit WHITE phase;
it must not be interpreted as a general flicker-free result. Numeric timelines
retain the black-centre interruption. This experiment motivates a separate
image-interruption metric, so replacing white with black cannot satisfy a gate.

Source rationale: pinned Wine11 winex11.drv/x11drv_main.c reads this AppDefaults
value; bitblt.c enable_direct_drawing bypasses a client window surface when it
is disabled. This changes the blank colour here, not the underlying startup
interruption. No product installer or normal-prefix workaround was added.
