# FastStone first-open flash — issue27

Current investigation, not a fix. The owner sees image → full white screen →
image on first fullscreen open. Record that exact sequence; an initial white
background before the first image is a different observation.

`tests/wine/first-open-probe.c` creates its own FastStone process with an
explicit synthetic image and expected center RGB. It never injects input.
It samples nine screen points only while that process owns the foreground
fullscreen window, rejecting invalid reads and foreground switches. An image
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

Next: reproduce headlessly, compare Windows, then locate the repaint/window
transition causing the white interval. The native path-button correction is
already delivered separately (issue21).
