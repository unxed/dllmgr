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
