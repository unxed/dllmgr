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
separate prefixes with the same font inventory. It verifies the actual ELF module
path, font counts/text-metric checksums, wall/CPU time and process peak memory.
The user's installed Wine is not touched. This mechanism is confined to the
research runner; no installer, registry override or catalog entry is provided.
