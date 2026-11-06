# CI timing

Move into a "CI timing" subsection of `docs/handoff.md` once that file is on
main (it is not there yet; creating it here would conflict).

## Before (faststone-research, runs of 2026-11-06, Actions API)

| Job / step | Normal | Worst seen | Cause |
|---|---|---|---|
| build (apt gcc-mingw) | under 1 min | 34 min | stalled apt mirror, run 42268151952 |
| wine (apt + 3 exes) | 1-2 min | - | - |
| faststone85 x3: Wine install | 60-80 s | 15 min, cancelled (3 of 5 runs) | WineHQ apt install stalled |
| faststone85 x3: capture | about 1 min | - | - |
| patched: Wine install | 70-80 s | 19 min | same stall |
| patched: check-fixes (Wine build) | 4-5 min | - | - |
| patched: 192 DPI comparison | 2-3 min | - | - |
| whole run | 8-10 min | 34 min | apt/WineHQ stalls, not the Wine build |

`patched` normally takes about 8 min; the 20 min seen came from the install
stall. No Wine-build cache was added: the build is under 5 min.

## Fail-fast limits (after)

Install steps use `tests/wine/ci-install.sh`: curl and apt timeouts, 150 s per
attempt, one retry, process dump on a stall. Job limits: build 8, windows 5,
windows-app 8, wine 11, faststone85 11, patched 20 (check step 12,
record_attempt 600 s). Failures and timeouts dump `ps` and apt logs and kill a
stuck wineserver. Anything above these is abnormal. After-timings were not
measured (validation run skipped by owner decision).
