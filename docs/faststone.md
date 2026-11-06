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
- Never install an unproven fix or replace a core/Unix-backed Wine DLL through
  the native-DLL installer. Keep unsupported mechanisms explicit.

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
