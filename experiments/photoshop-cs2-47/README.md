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
