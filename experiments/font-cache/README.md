# Experimental font-cache investigation

Research only, not a packaged fix or a supported native-DLL override.
The system Wine and the user's prefix are never patched by these scripts.

Actual Wine 11.0 / laptop observations (2026-11-07): enumerating 3256 font
records takes about 302 ms on the first walk and 3 ms afterwards. Creating,
selecting and measuring one sample in every record takes 2.4–2.5 seconds on
both passes, almost entirely process CPU. Selecting without text measurement
is about 0.8–1.0 seconds. Font metrics alone are 0.6–0.75 seconds. These are
standalone public-API measurements, not timings of the entire Draw Board.
The app itself opens Draw Board in roughly 6 seconds on this machine.

Pristine Wine 11.0 source db11d0fe6a169c457e23d007e20404643d067aa8 has
UNUSED_CACHE_SIZE 10 in dlls/win32u/font.c (active objects are separate; the
current insertion check can retain eleven unused objects). With a fixed small
set, repeated measurements are fast at 4/8 records and much slower at 12+.
See local-cache.txt. First tests used GetTickCount, whose resolution produced
misleading zero values; the archived version uses QueryPerformanceCounter.
No font names, user paths, photos or application data are published.

The one-line experimental patch raises that cache to 4096. This is a hypothesis,
not a validated fix: memory cost, invalidation, functional behavior and real-app
benefit still need testing. It may improve repeat walks without helping cold
startup. No complete explanation of the six-second delay is claimed.

The branch CI builds baseline and patched win32u Unix modules from the exact
source, uses each only in its own disposable copy of Wine 11.0, and initializes
separate prefixes with the same font inventory. While the benchmark is paused
after acquiring its display context, the Linux runner finds the benchmark's
own PID, requires its `/proc/<pid>/maps` to contain the expected ELF module, and
records that process's resident memory. It also records font counts,
text-metric checksums, wall/CPU time and peak memory. The user's installed Wine
is not touched. This mechanism is confined to the research runner; no
installer, registry override or catalog entry is provided.

Harness history: run 42413875048 found that Wine does not expose the Windows
executable path in the app process's Linux command line, so command-line based
PID discovery failed after the benchmark completed. Run 42414249062 passed with
the corrected approach: find the live PID by the expected `win32u.so` mapping
itself, then record that mapping and the same PID's resident memory.

Hosted evidence for harness commit `bddd53857fb0eb9440e6d403269f0b112033fc73`:
[CI run 42414361269](https://github.com/unxed/dllmgr/actions/runs/42414361269)
passed, including the stock and enlarged-cache module builds and the external
Linux `/proc/<pid>/maps` proof for both phases. Both enumeration phases saw
2112 callbacks, zero operation errors, and matching checksums in every mode:
mode 0 `cbf29ce484222325`, mode 1 `d5a6a3d12297d91c`, mode 2
`cbf29ce484222325`, and mode 3 `02650aa22492332d`. Mode 1's wall times
(stock/cache4096) were 977/1088 ms cold and 945/161 ms warm; mode 0 was
105/125 ms cold and 1/1 ms warm; mode 2 was 209/147 and 207/147 ms; mode 3
was 216/148 and 216/149 ms. These are standalone enumeration and measurement
results, not real-app startup timings.

In the separate cache benchmark, repeated time per pass for 4, 8, 12, 16, 32,
and 128 fonts was 0.047, 0.092, 2.150, 2.842, 6.578, and 40.149 ms on stock,
versus 0.047, 0.094, 0.138, 0.185, 0.377, and 1.596 ms with the enlarged
cache. First-pass times for the same sizes were 0.996, 0.903, 1.057, 2.943,
6.760, and 40.364 ms on stock, versus 1.019, 0.879, 1.070, 1.069, 4.342,
and 37.626 ms with the enlarged cache. This supports the cache hypothesis for
this synthetic repeated-measurement workload only; real-app A/B evidence is
still required.

At the explicit post-`GetDC` ready pause, process RSS was 25996 kB on stock and
26256 kB with the enlarged cache. This snapshot is before the benchmark fills
font-cache entries, so it does not measure retained-font memory cost. The
`/usr/bin/time -v` wrapper reported 18324/18144 kB maximum RSS for the Wine
launcher command, but may miss the Wine child process peak; it is not a
reliable child-process peak-memory comparison.

## Actual FastStone: this candidate did not help

Local A/B/B/A on 2026-11-07 used official FastStone 8.5 x86, synthetic white
800x600 BMP, a fresh portable profile per launch, a disposable win64 prefix
at 192 DPI and the same host font inventory. The private runtime materialized
its Unix modules and launchers; unchanged PE/data files were read through
symlinks. The installed system win32u.so hash was identical before/after.
The original FastStone profile/default Wine prefix were not used.

The first default-mode attempt ran to Draw readiness but **failed the expected
x86_64 Unix-module mapping proof**: it used the other architecture. These
initial timings (startup reply 2116 ms, Draw reply 6373 ms) are not an A/B
comparison. The retry forced `WINEARCH=wow64` in the owned runtime/prefix and
required the FSViewer.exe process's Linux maps to contain the exact private
x86_64 win32u.so on every run. This does not establish parity with the owner's
ordinary Wine loader mode.

`local-faststone-abba.json` records the four valid runs. Draw mapping/reply:
stock 7119/7120 and 7013/7323 ms; cache4096 6844/6850 and 7636/7640 ms.
Mean reply: **7221.5 ms stock versus 7245 ms candidate**. Startup reply was
1556/1661 ms stock and 1690/1572 ms candidate. There is **no demonstrated
application speedup**; do not install this cache enlargement for FastStone.
Two samples per variant cannot establish a small improvement/regression.

Unlike the earlier microbenchmark's pre-cache RSS, these are samples of the
actual FSViewer.exe Linux process after Draw mapped: stock 160440/160528 kB,
candidate 161304/163108 kB. Sampled process peaks were 189784/193024 kB stock
and 184052/183400 kB candidate; 50 ms polling can miss the true peak. These
figures do not isolate retained font-cache memory. WM_NULL reply remains a
readiness proxy, not proof of final painting or all input handling.

The focused public-API observer is `app-observer.c`; compile it with the
existing tests/wine include path and listview-probe.c. It launches its own
process, measures startup and one Draw open, pauses for external memory/maps
sampling, then terminates only that owned process. No synthetic input is sent
unless that application's window is foreground. Next profiling should find
actual Draw cost rather than extrapolating from repeated text measurement.
