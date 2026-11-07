# Local FastStone checkpoint, 2026-11-07

Environment: actual installed FastStone 8.5 x86, Wine 11.0, Linux x86_64,
win64 prefix, 192 DPI, 3072x1728 screen. All application probes use a generated
800x600 white BMP. No user photo, prefix, application settings database or
whole-desktop screenshot is published here.

The complete installed faststone-v2 bundle was restored after every temporary
test. The last isolated test explicitly verified both DLL hashes, override
registry values and the complete managed state against its initial snapshot;
original FastStone settings were restored. No temporary font remains installed.

## Measured results

Times are window mapping / first WM_NULL reply, milliseconds. They are proxies
for readiness, not completed painting or a full responsiveness benchmark.

| Configuration | Startup | First Draw | Second Draw | Stroke |
| --- | --- | --- | --- | --- |
| Installed full bundle | 1462 / 1473 | 6108 / 6457 | 6329 / 6342 | ff0000, 3642 pixels |
| Stock DLLs, temporary undo | 1445 / 1479 | 5778 / 6102 | 6392 / 6393 | 000000, 3642 pixels |
| Only GDI+ candidate, stock comctl32 | 1466 / 1489 | 5752 / 5772 | 6104 / 6106 | 000000, 3642 pixels |
| Bundle, scoped Fontconfig experiment | 1937 / 1973 | 12142 / 12182 | 12387 / 12427 | ff0000, 3642 pixels |

**Unresolved discrepancy:** the isolated GDI+ attempt did not reproduce the
red stroke of the full bundle. The pencil button was selected and its colour
control was red in the capture. This attempt has no loader trace, so effective
native/builtin loading is not established. Do not declare the per-fix real-app
gate complete until this is explained. The synthetic GDI+ reproducer and the
full-bundle CI/local results remain separate evidence.

The scoped Fontconfig exposed 78 files to fc-list instead of the host's 2543,
but did not isolate the Wine font universe: the API benchmark callback count
increased from 3256 to 6444. Measuring/selecting every font took about
2.0–2.4 seconds normally and 4.8–5.1 seconds with that configuration. A normal
run afterwards returned to 3256 callbacks and 2.0–2.1 seconds. This failed
experiment is not evidence that removing host fonts helps, and was not retained.

The separate font+GDI+ trace perturbs timings (Draw ~6.9–7.0 seconds). In the
main app it shows four full enumeration walks of 6512 charset records each,
taking about 25–321 ms, separated by multi-second work. The walk alone does
not explain the whole delay. Each of eight Wine process IDs also loads 2955
Fontconfig face records; face records are not unique font files. Trace totals
include ~100k font selections and ~370k glyph-metric records in the app thread.
The raw trace is private; sanitized aggregate findings are retained here.

## Reproducing the isolated experiment

`isolated-pencil.py` is an experimental runner, not the normal installer. It
requires FIW_TOOLS pointing at the pristine fix-it-in-wine tools checkout and
an already-managed, two-module faststone-v2 installation. It temporarily undoes
the bundle, tests stock, tests the current GDI+ file alone, then restores both
files/registry/state in finally and verifies restoration. It also checkpoints
and restores the supplied settings directory. Run only with no existing
FastStone process and no other prefix writer. Supply explicit --prefix, --exe,
--image, --settings, --observer and a new --output directory. The generalized
archive is syntax checked; the recorded run used this procedure locally before
parameterization. Keep output private: the observer captures the desktop.

Compile the observer from tests/wine/app-observer.c with listview-probe.c and
-lgdi32. Build synthetic fixtures using tests/wine/make-images.py in a scratch
working directory. The font-enum-bench.c helper is read-only; compile with
mingw and -lgdi32. It records enumeration and enumeration+font-text-measure
cost separately, with two passes each. It does not reproduce Draw Board.

## Next steps

1. Trace actual GDI+ loading in the isolated attempt before changing the fix.
2. Resolve new self-intersections in the experimental font, then get the owner's
   visual acceptance. See ../tahoma-bold/README.md for successful and failed steps.
3. Collect a real physical mouse sample when the owner returns; passive tools
   are ready in tools/cursor-sample.py and tests/wine/cursor-probe.c.
4. Reproduce transient path-field artifacts; view switches clearing an artifact
   are a clue, not an established fix.
5. Keep startup/Draw timing work separate from font rendering and pointer speed.
