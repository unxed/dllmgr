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
