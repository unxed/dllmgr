# CI timing

See also the current recovery steps in `docs/handoff.md`.

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

## Investigated failure after #17

In run [42276979629](https://github.com/unxed/dllmgr/actions/runs/42276979629),
`faststone85 (96)` failed before launching Wine or FastStone. Both APT install
attempts reached exactly 150 seconds; the six-minute step timeout was not hit.
Quiet APT output hid the active URL and no package configuration appeared in
the first attempt's logs. The exact download/resolver stall is not established.
The same 96-DPI job in run 42278157255 installed successfully in 76 seconds
and completed its captures. This is not evidence of a DPI-specific app failure.

The install helper now keeps download URLs and complete per-attempt logs,
stops on repository setup/pipeline errors, passes package arguments literally,
and bounds dpkg recovery. Failed jobs upload `ci-install-<job>` artifacts.
The two 150-second attempt limits remain; raising them would hide the stall.
