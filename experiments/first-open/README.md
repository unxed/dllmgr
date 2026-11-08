# FastStone first-open flash — issue27

Current investigation, not a fix. The owner sees image → full white screen →
image on first fullscreen open. Record that exact sequence; an initial white
background before the first image is a different observation.

`tests/wine/first-open-probe.c` creates its own FastStone process with an
explicit synthetic image and expected center RGB. It never injects input.
It samples the centre while that process owns the foreground fullscreen window,
then checks the remaining eight points only for a white candidate, rejecting
invalid reads and foreground switches. An image
is recognized by the explicit fixture colour; white means all nine samples
are white. Sampling is not exhaustive frame capture and can miss short events
or frames before foreground acquisition. Failed reproduction is not resolution.

Build (with the existing public-API listview observer dependency):

```sh
x86_64-w64-mingw32-gcc -O2 -Wall -municode \
  -o first-open-probe.exe tests/wine/first-open-probe.c \
  tests/wine/listview-probe.c -lgdi32 -lshell32
```

Run under the private runtime environment for the exact installed EXE, then
pass `EXE IMAGE RRGGBB`. The observer is a different process and gets ordinary
DLL loading; its selected FastStone child gets the private DLLs. Preserve and
restore installed settings. Use only synthetic images and keep full desktop
captures private until sanitized. Never terminate an unrelated running copy.

## First laptop observation (2026-11-08)

Wine11.0, 192DPI, installed FastStone8.5 and private faststone-v3. A uniform
800x600 BMP (RGB f0cd5a) produced initial white at2000ms, then the expected image
at2202ms. No image→white→image sequence was observed in589 valid samples over
approximately7s after first image;174 earlier/non-owned samples were skipped.
Settings restored. This first run preceded the invalid-read guard; repeat with
the guard before treating the initial white as validated. No fix or absence of
the owner's bug is claimed.

## Reproduced JPEG sequence (2026-11-08)

With the invalid-read guard enabled, a generated 800x600 JPEG (decoded centre
RGB f0cc5a) reproduced the reported sequence on the same installed private v3:
image at 2376 ms, nine white samples at 2520 ms, image restored at 2771 ms.
The observed white interval was 251 ms. See [the raw timeline](laptop-jpeg.txt).
The probe exited successfully and the installed settings were restored.
One BMP and one JPEG run do not establish a format-specific cause.

Further testing must use hosted CI or a separate headless display and a disposable
prefix. The owner explicitly requests no test windows on the active desktop.
Do not reuse an existing user-prefix Wine server on another display. Full-screen
captures remain private until inspected for unrelated desktop content.

## Headless stock Wine (2026-11-08)

A separate Xvfb :93 (3072x1728, 192 DPI), Metacity, and the existing disposable
`avif-wine-validation/prefix` reproduced the sequence with portable FastStone8.5
and **stock** Wine11.0: image2114 ms → white2140 ms → image2315 ms (175 ms).
See [untraced timeline](headless-stock.txt). No test used the active display or
normal prefix. This does not implicate the installed private DLL fixes.

A separate `timestamp,+win` diagnostic run also reproduced it. The foreground
TFullScreenWindow HWND, style and geometry remained the same at all sampled
phases; see [traced timeline](headless-traced.txt). A second visible full-screen
TForm existed underneath. The trace contains window creation, reparenting and
surface changes during startup. These are leads, not an established cause.
Traced timing (356 ms white interval) must not be used as performance evidence.

The Xvfb executable was reused read-only from another local investigation's
unpacked Ubuntu package, on our own separate display. No system package was
installed, and no other display/server was stopped.

Next: compare the cold-launch sequence with real Windows via the manual
`First-open research` workflow, then locate the repaint/window transition. A
missing expected image fails the probe; absence of a sampled flash alone does
not establish a fix. The native path-button correction is delivered separately
(issue21).

## Windows baseline and rejected capture shortcuts

[Windows CI 42497502733](https://github.com/unxed/dllmgr/actions/runs/42497502733)
at ea5b75a succeeded: expected JPEG image at2406 ms, no sampled white transition.
However, it collected only44 valid samples at1024x768/96DPI; screen GetPixel is
slow there. This is a preliminary baseline, not proof of absence or a matched
192DPI/high-resolution comparison. See [Windows timeline](windows-first.txt).

Two attempted faster capture methods were rejected on headless Wine192DPI:

- StretchBlt to a6x6 DIB did not recognize the expected image at all (exit5),
  and took up to183 ms per capture; do not adopt it or infer that the bug vanished.
  See [failed timeline](rejected-stretch.txt).
- Full-screen BitBlt to a DIB recognized the final image but missed the short
  first image and took up to213 ms per capture. It collected only75 samples,
  less than the original GetPixel method. See [timeline](rejected-full-blit.txt).

The original guarded nine-point sampler remains in use. These rejected methods
must not turn the regression green by losing the first image.

The timestamped +win,+gdi run aligned the white phase with the first flush of a
new fullscreen window surface (white at128933.112s, initial surface flush at
128933.104s). Wine's window_surface_create initializes pixels to0xff. This is a
specific source/trace lead, **not proof** that changing initialization or forcing
an early paint is correct. [Traced phases](headless-gdi-traced.txt) retain the
same foreground HWND. The trace is local in local-first-open-headless/gdi-trace;
only synthetic timelines are published.

Next steps: a minimal public-API popup/delayed-paint reproducer compared on
Windows/Wine, and a denser trustworthy native Windows capture. Preserve the
reproduced failure as the gate; do not ship a hardcoded white-to-black change.

`tests/wine/window-first-paint.c` is the next minimal public-API diagnostic:
paint a synthetic underlay, show a popup without a background brush, sample its
unpainted centre, then explicitly paint it. The manual Windows workflow runs
this alongside the application observer. It records observations rather than
asserting a contract for uninitialized window pixels; a matching blank popup
alone would not establish that this is FastStone's exact path.

## Minimal popup comparison (2026-11-08)

At ea44732, [Windows CI42498050053](https://github.com/unxed/dllmgr/actions/runs/42498050053)
passed. The minimal popup retained the yellow underlay before painting on
Windows96DPI; local headless stock Wine192DPI showed black until painting.
See [Windows samples](popup-windows.txt) and [Wine samples](popup-wine.txt).
This establishes a difference in this synthetic unpainted-window observation,
not yet FastStone's specific white flash or a guaranteed API contract.
Next: correlate surface invalidation/flushing and the first partial paint in
FastStone with a refined synthetic case; avoid simply replacing one flash colour
with another. The actual-app Windows run again had44 valid samples, so its
unsampled intervals remain a limitation.

## Upstream feedback (2026-11-08)

The verified symptom is published, words only, as
[Wine60721](https://bugs.winehq.org/show_bug.cgi?id=60721#c0).
ALL FastStone and the exact phrase white flash were searched. Wine59109
through comment6 describes initial surface flushing in a fullscreen game;
that is a concrete lead, but its Direct3D client-surface transition is not
established in FastStone. Wine57839 is another possible redraw relation.
No duplicate or shared cause is asserted. The report explicitly retains
the sparse Windows-sampling limitation and does not claim a fix.

Next: examine whether the first partial image paint and later surface
creation/flush replace already-painted pixels. Compare an explicitly
partially painted synthetic popup on Windows and Wine. Keep all tests
on a hidden display or hosted runners.

## Denser native observation (in progress)

The earlier Windows run spent nine slow desktop GetPixel calls on every
iteration, even while a solid expected image was already visible. The observer
now reads the centre first and checks the other eight only when the centre is
white. A white phase still requires9/9 white points and foreground ownership
before/after sampling. Output records actual points read and capture duration.
This reduces routine capture overhead; measured sampling density must still be
checked on native Windows. It does not make the probe frame-exhaustive.
