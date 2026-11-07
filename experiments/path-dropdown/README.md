# FastStone path dropdown research (dllmgr #21)

Keep two symptoms separate: the owner's old, severe path-row corruption has
no reliable reproduction; the press/release behavior of the dropdown arrow
needs comparison with Windows. A clean official portable 8.5 profile keeps
this experiment independent of the owner's settings.

`tests/wine/path-observer.c` launches only the supplied application, finds the
combo containing the generated `browser` folder, and records initial, hover,
down, held, up, second down/up and Escape states. Each screenshot is cropped
to the synthetic path and dropdown area. It reports public combo state and
focus/capture; it does not inspect native Windows internals. Mouse release is
sent even if a capture fails. Input aborts if the owned browser loses focus.

The Path dropdown research workflow runs native Windows and stock Wine 11.0
at 96/192 DPI. Compare Windows and Wine at **96 DPI** for exact pixel geometry;
Windows hosted desktop DPI is reported, not assumed. Wine 192 DPI is a separate
HiDPI check, not a claim of pixel parity with Windows at 192 DPI.

This branch is investigation only: no new DLL fix is installed.

First run 42413956268 at 994c51d: both stock Wine jobs passed, but native
Windows did not find the synthetic path combo. No Windows/Wine difference is
claimed from that run. The probe now captures its owned initial/failure
window and child class geometry so this harness failure is diagnosable.

Local clean portable profile on the owner's installed Wine/prefix also passed
all eight capture states. The installed FastStone profile hashes were identical
before and after; the temporary C-drive fixture was removed. The severe old
path-row artifact did not appear in this single attempt.

Run 42414270400 at 2dc9ce9 passed Windows and both Wine jobs. The measured
open/pressed/capture transitions agree in all eight stages. Button painting
differs substantially, but the initial window widths and OS themes also differ;
these images do not isolate a Wine defect. Next capture fixes the client area
at 900x600 logical pixels and separately disables theming on the combo with
public SetWindowTheme; each mode starts from a fresh portable profile.

Run 42414539727 at 7c94278: matched client size gives the **same 481x24 px
combo size** on native Windows and Wine96. The eight themed-state transitions
still agree. Windows uses NormalColor; Wine uses Blue, so themed pixel colors
are not an identical baseline. Native classic capture succeeded, but Wine's
SetWindowTheme(combo, L"", L"") returned 0x8007007b (invalid name), aborting
that mode safely. Wine uxtheme's property setter calls GlobalAddAtomW on the
empty value. The next probe uses nonempty, nonexistent space class names to
disable theming on both systems; no prefix-wide theme setting is changed.
