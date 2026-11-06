# FastStone fix set

Audit date: 2026-11-06. Target application: `FSViewer.exe`. Keep one source
patch and reproducer per Wine bug, and build the application's combined DLLs
from those patches together. Installing independent builds of the same DLL
one after another would lose the earlier fixes.

## Bugzilla audit

Read the descriptions and all comments of the nine open results from
<https://bugs.winehq.org/buglist.cgi?quicksearch=faststone>. The search includes
historical issues and unrelated mentions; it is not a list of nine current
FastStone defects. Bugzilla status alone does not establish reproducibility.

| Bug | Finding and next action |
| --- | --- |
| [41438](https://bugs.winehq.org/show_bug.cgi?id=41438) | Crop dialog behind fullscreen. Reporter could no longer reproduce with FastStone 5.6 and Wine 11 rc3 (comments 5-6). Retest before considering a backport; do not install a speculative window-management change. |
| [43490](https://bugs.winehq.org/show_bug.cgi?id=43490) | Old Microsoft comctl32 v5 lacks exports now required by Wine shell32. This is a failed workaround, not a single defect in Wine comctl32. The original thumbnail symptom is tracked separately as 5129/59251/59609. Fix builtin Wine rather than redistribute Microsoft DLLs. |
| [48872](https://bugs.winehq.org/show_bug.cgi?id=48872) | Missing filenames in FastStone 7.5. [MR 10093](https://gitlab.winehq.org/wine/wine/-/merge_requests/10093) measures empty list-view labels using a space, but its review identifies an unwanted painted selection rectangle. Compare metrics and painting with Windows; a fix must preserve both. The reporter's successful FastStone 5.6 test does not resolve the 7.5 case. Screenshot: attachment 66805. |
| [48874](https://bugs.winehq.org/show_bug.cgi?id=48874) | Pencil strokes stay black in FastStone 7.5; other shapes respect the selected color. Still reported with Wine 11.2 and FastStone 7.5, while 5.6 works (comments 7-8). Video attachment 66809 demonstrates changing the color and drawing black strokes. Identify the API and add a pixel-level Windows/Wine reproducer before choosing a DLL. |
| [52179](https://bugs.winehq.org/show_bug.cgi?id=52179) | NFS Underground 2 installer artifacts. FastStone is mentioned as an image viewer that displays the source image correctly. Excluded from this fix set. |
| [59251](https://bugs.winehq.org/show_bug.cgi?id=59251) | Two symptoms in the fullscreen strip: missing thumbnails and inactive wheel. The thumbnail symptom matches 59609; the wheel needs its own reproducer. Wine's icon-view wheel handler only calls vertical scrolling. Test horizontal icon layouts against Windows. |
| [59609](https://bugs.winehq.org/show_bug.cgi?id=59609) | Existing packaged fix for LVM_GETITEMPOSITION returning client coordinates in icon/small-icon view. Keep it as a separate catalog fix and include it in the combined build. |
| [60301](https://bugs.winehq.org/show_bug.cgi?id=60301) | RMB hold sends an early release since Wine 11.17, with duplicate input reported by another user. Wine 11.16 is the reported good version. Candidate change: [44a822d2374c](https://github.com/wine-mirror/wine/commit/44a822d2374c71ee74fa8dc930b63f5a8e9ae256), raw XInput2 button handling. Requires real-input regression evidence. `winex11.drv` has a Unix component and cannot be installed as an ordinary native DLL. This fix does not apply to Wine 11.0. |
| [5129](https://bugs.winehq.org/show_bug.cgi?id=5129) | Historical main-window thumbnail issue. Reporter no longer reproduced that symptom in Wine 11 with FastStone 5.6 (comments 43-44); comment 45 explicitly separates the remaining fullscreen strip problem as 59251. No additional patch justified yet. |

## Packaging and acceptance

- Individual entries remain keyed by Wine bug, with source, base Wine tag,
  SHA256, license, a minimal reproducer and exact CI evidence.
- The `faststone` set names the verified fixes for the installed Wine and
  application versions. It must say which bugs are included, already fixed,
  inapplicable or still under investigation.
- Compose all selected source patches for each module, then build that module
  once. A fix set is not a sequence of overwrites of the same DLL.
- Verify an unfixed failure, unchanged Windows behavior, fixed success and
  byte-for-byte rollback. Check both common-controls v5 and v6 where relevant.
- Preserve the user's original DLL and previous registry value when upgrading
  from the existing 59609 script to the combined set.
- Applying an individual fix replaces the current selection. Switching from
  the bundle to a single fix also restores any DLL and override that the
  selected fix no longer needs.
- Never install an unproven fix or replace a core/Unix-backed Wine DLL through
  the native-DLL installer. Keep unsupported mechanisms explicit.

Only 59609 has published binaries. The other scripts and the bundle are for
testing. Use `--build` with a disposable Wine prefix for candidate builds.

## Additional user-critical symptoms

Reported on 2026-11-06, FastStone Image Viewer **8.5**, Wine **11.0**, i386
program in a win64 prefix. The current prefix reports **192 DPI**. Keep these
reports separate from the older FastStone 5.6/7.5 test cases. They have no
assigned Wine bug number yet. Use synthetic images for public evidence.

| Local ID | Symptom | Evidence needed / acceptance |
| --- | --- | --- |
| FS-geometry | File thumbnails and folder preview images extend outside their tiles; the format label at the bottom right also overflows. | Compare item, icon, label and select rectangles at 96/144/192 DPI and several thumbnail sizes. Include both folder and file tiles, portrait/landscape images and format text. Images and format labels must fit their assigned regions. Inspect MR 10017 as a hypothesis, not an accepted fix. |
| FS-names | File and folder names under tiles are absent. | Check the application's display settings and compare with Windows. Names are normally displayed; missing names are not an expected consequence of HiDPI. Cross-check 48872 and include an actual 8.5 application test, not just a 5.6 result. |
| FS-path | The folder-path field above the thumbnails showed transient drawing artifacts; reproduction is not known. | Keep this as intermittent, unresolved. The user observed that switching Thumbnails → Details → List may clear the artifact; compare a full repaint with view-dependent layout/cache invalidation. Capture the screen immediately with a timestamp and note scrolling, resizing, DPI changes, folder changes and occlusion before it happened. Compare repaint/resize and invalidate behavior with generated folder names; absence in one run is not a fix. |
| FS-fonts | The fullscreen left panel's “Rotation, sizes, text” heading and some other interface text render poorly. | Collect the actual fonts selected by Wine, font smoothing, logical/physical DPI and the affected controls. Compare Cyrillic and Latin text at the same DPI on Windows. Fontconfig's fallback result alone does not prove which font Wine used. |
| FS-wheel-speed | Mouse-wheel scrolling is unacceptably slow. | Measure pixels and items per detent plus elapsed time with identical images and window size at 96/144/192 DPI. Separate the main thumbnail grid from the horizontal fullscreen strip. Compare configured wheel lines and fractional wheel events. HiDPI is a hypothesis, not an established cause. |
| FS-draw-start | Opening Draw Board takes about 5 seconds (user timing). | Measure keypress-to-interactive-window time, first and subsequent opens, with tracing disabled. Then collect bounded font/GDI+/module traces to locate the delay; compare 7.5 and 8.5. |
| FS-start | Startup takes about 2–3 seconds (user timing); faster startup is desired. | Measure process start to usable viewer/browser separately, cold and warm, with the same local synthetic image/folder. Separate Wine prefix initialization, font discovery, codecs, directory scanning and thumbnail database costs. Preserve correctness and user settings. |

| FS-middle-button | Middle-button actions may differ between browser, windowed viewer and fullscreen modes; expected behavior has not been verified. | The bundled 8.5 help (ViewingImages.htm) specifies middle click as Full Screen ↔ Browser; Enter/F also cover Windowed View. Check the relevant mouse settings for each mode; compare press/release, short click and hold on Windows and Wine. Preserve configurable actions. |

For FS-path, a short capture recipe is to run the app under the existing
`wineprobe.py` load preset with a bounded timeout, keep the log local, and take
a screenshot as soon as the artifact appears. Record the event timestamp and
the immediately preceding actions next to that log. Enable narrower control
or font tracing only for a follow-up attempt; heavy tracing distorts timing.

Use the proposed skill recorder from `contrib/fix-it-in-wine-learning.patch`
for experimental commands. Retain failed hypotheses and exact recovery details,
including test-harness failures, rather than only the successful final run.

## Next: Far Manager

After FastStone, perform the same audit and per-bug reproducer work for
[Far Manager](https://bugs.winehq.org/buglist.cgi?quicksearch=far%20manager&list_id=873209).
That unquoted quick search currently returns 98 results, many unrelated
(including Far Cry and generic window-manager reports). Direct title matches
include 50606 (TTY resize), 51650 (console support), 59724 (console colors) and
59130 (startup hang). Read linked console bugs too; do not assume this short
list is exhaustive. Distinguish the GUI conhost and Unix-terminal paths.

## GUI

The manager's GUI is already specified in [concept section 11](concept.md#11-gui-on-gowidgets)
and iteration I4. It uses goWidgets and the same underlying operations as the
CLI: select a prefix/application, inspect installed rules, add/remove variants,
check by running, and update the catalog. It has not been implemented.

Application fix sets should appear as selectable sets of individual fixes.
The install plan must show the combined modules, covered bugs and applicability;
removing one fix must rebuild/select the remaining combination and preserve the
original baseline for a complete uninstall. Keep composition and rollback logic
in the manager, outside the GUI.

## Input and timing observations (official portable 8.5)

The shared `app-observer.exe` launches a generated white BMP, uses real input,
and logs visible-window geometry and WM_NULL round trips. These are proxies for
readiness, not proof of completed painting or a full performance benchmark.
Windows run [42169416997](https://github.com/unxed/dllmgr/actions/runs/42169416997)
observed a clean process exit (code 0) after middle click when started with an
image file. The same Wine observation therefore does not establish an input
bug. The bundled help's Browser ↔ Full Screen description needs to be checked
from browser mode as well. Enter kept the process alive in this experiment.
Draw Board mapped in about 0.45/0.39 seconds on that Windows runner; hardware,
fonts, image size and cache state differ from the user's machine.

The earlier 192 DPI Wine capture returned a 1536×864 bitmap on a 3072×1728
Xvfb screen. It shows a folder preview extending past its tile and a missing
folder name. The right-hand grid is clipped, so file previews and their
format labels cannot be assessed from that capture.

The observer now captures the whole screen. The browser scenario includes
named portrait and landscape fixtures and a folder preview, logs list-view
rectangles, records wheel input on the fullscreen strip and thumbnail grid,
and tries a middle click after entering fullscreen from the browser. It also
captures the address field before and after an explicit repaint. The path
artifact still needs a repeatable sequence of view changes.

The 96/144/192 DPI Wine jobs run independently. The 192 DPI job traces fonts
in a separate left-panel run. The Draw Board check uses the Delphi form class
as well as the caption. One earlier Wine run timed out looking for the
caption while its screenshot already showed the board. Mapping and the
first response to `WM_NULL` are recorded separately.

The deep Wine run also compares the portable x86 application at 192 DPI in
two disposable win64 prefixes. It uses the same fixture and observer in both,
and applies the just-built i386 `comctl32_v6` and `gdiplus` through the bundle
installer in the second prefix. The `faststone85-192-comparison` artifact
contains the baseline and patched captures, the application-specific native
load trace, and the byte-for-byte undo check. Compare the browser and strip
captures before drawing conclusions about the remaining FastStone issues.

The [192 DPI comparison](https://github.com/unxed/dllmgr/actions/runs/42236384573/artifacts/13511857686)
shows file and folder names (including Cyrillic) in the patched browser. The
first label's width changed from 0 to 276 pixels. The folder preview and BMP
badges still extend past their tile frames. The same x86 process logged native
loads of both DLLs. Wine reported the logical `system32` path for GDI+, which
the initial check rejected despite the successful load. Both files were
restored byte for byte on undo. This run exercised opening Draw Board; the
GDI+ pencil-color test remains a separate probe.

## Gate for Wine Bugzilla reports and follow-ups

Before posting a report or a candidate fix to Wine, reproduce the behavior
described in the relevant Wine report with a test that fails on the original
Wine build and passes with only the proposed change. Record the application
version, Wine build, architecture, display setup, exact command, and results.
Also exercise the affected controls visually in the real application and
record the steps and captures. A synthetic probe alone, an unverified app
capture, or a bundled build with several changes cannot establish this gate.
Existing reports get follow-ups when their original case meets the same gate.
