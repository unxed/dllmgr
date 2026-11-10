# #47 Alt+wheel zoom redraws in visible steps

Stand (2026-11-10, runtime v12, dllmgr run, t46.png, 192 DPI): zoom47.sh
records the screen at 30 fps (ffmpeg x11grab) while Alt+wheel up is sent
at the image centre. Distinct frames after the first notch (100 % -> 110 %):
f021, f022, f024, f026, f028 within ~0.25 s; stand-v12-zoom-frames.png
(f020 f021 f022 / f024 f026 f028): f026 shows the zoomed image only partly
redrawn (band at the bottom and a seam on the right still from the old
zoom) before f028 completes it.

Windows reference: tests/wine/ps35-measure.ps1 #47 stage (screenshots
every capture after each notch, zoom-frames.json), CI run 42731155874.

Windows (CI run 42731155874, Server 2025, 96 DPI, 1600x1200 test image at
33.3 %, windows-ci-zoom-frames.png: before, 66 ms, 1100 ms, 1150 ms after
the notch): the zoomed image (36.67 %) is complete in the first capture
66 ms after the wheel event; later changes are only the title. No partial
redraw is visible. On the stand the same step takes ~250 ms with 4
intermediate frames, one of them half redrawn. Next: where the time goes
(perf of the zoom on the stand) and Wine's surface flush every 50 ms while
the application is still drawing.

## 2026-11-10: same kind of image as the Windows run

Stand (fresh CS2 reinstall, rt-cur3 = v14 code, 192 DPI), C:\ps47.png
(1600x1200 8-bit, 8x8 random blocks like the CI image), shown at 50 %,
one Alt+wheel notch, 60 fps capture (zoom47b.sh): the zoomed image appears
in one frame (frame 26; the only earlier change is the title, 116 ms
before). No partial frames. The partial redraws seen before were with
t46.png, a 16-bit document at 100 %. Whole-system perf of eight notches:
Photoshop 10 % CPU, the stand's software compositor (llvmpipe) 18 %, mostly
idle, i.e. not CPU-bound. Open: does the owner still see steps with v14,
and with which document (bit depth, zoom)?

## 2026-11-10: 16-bit on Windows, and Wine's flush ruled out

Windows (CI run 42803487934, 96 DPI, generated 16-bit 800x600 PNG,
tests/wine/png16.py, opened at 66.7 %): both Alt+wheel notches are complete
in the first capture 56-60 ms after the event; no partial frames.

Stand (separate display :96, prefix copy, rt-cur3, C:\t46.png 16-bit at
100 %, z16.sh, 60 fps): notch 1 changes the screen in two steps ~250 ms
apart (frame 53: 22491 px changed, 25398 px still differ from the final
frame; frame 68: final). With Wine's non-idle surface flushes disabled
(experimental DLLMGR47_NOFLUSH, not kept) notch 1 shows the identical two
steps (same pixel counts), so the steps are not Wine's 50 ms flush while the
application draws: Photoshop itself draws the 16-bit zoom in two passes
here. Caveat found: xdotool "keydown alt click 4 keyup alt" leaves the
menu bar active (File highlighted) after the first notch, so later notches
in one run are unreliable; use one notch per run.
Open: why Photoshop takes two passes on Wine but one on Windows (draw
time: 4x the pixels at 192 DPI? a timer it checks?). Owner question: which
documents show the jumps for you (8 or 16 bit, zoom level)?

Alt held for the whole capture (z16h.sh, like the Windows test): still two
steps, 133 ms apart (frames 45 and 53). Both steps repaint the whole image
area (difference masks), i.e. Photoshop draws a fast first pass and then
the final one. On Windows both land within the first 60 ms capture; on the
stand the final pass comes 130-250 ms later. Next (not started): where the
second pass waits (timer / idle detection in Photoshop's message loop under
Wine), e.g. +timestamp,+message,+timer trace around one notch.

## 2026-11-10: the owner's screen recording (8-bit photo, v18)

experiments/owner-2026-11-10/alt-wheel-zoom-artifacts.mp4 (25 fps, 3072x1728).
Frame differences: almost every zoom step changes the screen in two frames
(40 ms apart), first a part, then the rest. Frame 23
(owner-2026-11-10/zoom-frame23-mid-resize.png): the document window has
already grown (title "116%", status still "105.7%"), the zoomed image is
drawn inside the old extent with the old grey border, and the newly exposed
strips at the right and bottom show stale screen pixels (old image); the
next frame is complete. So the artifact is the window resize becoming
visible before the application's repaint: Photoshop resizes the document
window on zoom; X shows the larger window at once (new area = old screen
content), Wine's window surface with the new paint is flushed one frame
later. Windows (DWM) presents resize and repaint together.
Fix direction (not started): when a window grows, hold its X configure (or
the flush of the exposed area) until the application has repainted, with a
short timeout; or paint the exposed area from the surface immediately.

## 2026-11-10 evening: stand reproduction with Ctrl+= and a main-thread profile

z512k.sh (prefix-b, :96, t512.png 8-bit 512x512 at 100 %, Ctrl+= to 200 %,
60 fps capture): the document window size stays (1054x1054 px, set at
open); the zoom appears in steps ~30-50 ms apart: first the top-left tile
of the new zoom with the rest still old, then the rest. Photoshop paints
the zoomed image tile by tile.
Experiment DLLMGR47_HOLD (winex11: hold an application's resize until the
next flush) changed nothing: here no resize happens at the notch (trace),
so it is not the mechanism in this case (code kept only in the local tree).
Main-thread profile (DLLMGR_SAMPLE=2,3,go; the third field "go" starts the
sampler when Z:\tmp\dllmgr-sample-go appears, z512k.sh touches it at the
notch): before the notch the main thread is still busy in NtGdiGetFontData
(CoolType reading fonts 30+ s after start); at the notch NtUserSetWindowPos,
then ZwSetEvent (waking Photoshop's worker threads, "multiprocessor
support.8bx") and NtUserGetMessage idle; tiles arrive as the workers finish,
and Wine flushes the window surface each time the main thread goes idle, so
every tile batch becomes a visible frame. On Windows (CI, earlier) the whole
zoom is on screen within the first 60 ms capture.
Next: sample all threads (workers) to see why rendering takes 150-200 ms
here; and/or coalesce idle flushes within a frame interval.
