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
