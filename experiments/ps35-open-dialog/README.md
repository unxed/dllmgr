# #35 / Wine 34134: CS2 Open dialog keeps the Adobe dialog width (sandbox)

Stand: stock Wine 11.0, Xvfb 3072x1728 @192 DPI, Metacity `--compositor=none`,
CS2 Tryout via scripts/sandbox-install-cs2.sh. Scenario script:
tests/wine/ps35-open-toggle.sh (File > Open, Use Adobe Dialog, Use OS Dialog).

Reproduced exactly as on the owner's laptop (X sizes): OS 1192x1136 ->
Adobe 1520x1136 (a different window) -> OS (same window as before) 1520x1136.

Who resizes (WINEDEBUG=+win, and +relay limited by RelayInclude to
user32.SetWindowPos/MoveWindow/DeferWindowPos to get return addresses):

- OS dialog hwnd 0x20612 (`#32770` "Open", owner Photoshop main window).
  comdlg32 sizes it 565x421, then 604x602 (logical; Photoshop is DPI-unaware).
- Adobe dialog hwnd 0x20928: created 770x522; then
  `SetWindowPos(0x20928, 465,87, 760x602)` (position and height of the OS
  dialog, width 760) from **versioncueui.dll**; Wine's calc_winpos applies the
  minimum track size and makes it 768x602.
- Switching back: `MoveWindow(0x20612, 465,87, 768,602, FALSE)` from
  **versioncueui.dll** (return address 0x09d866bd, module at 0x09d60000).

So the width growth is Adobe's own explicit resize of the OS dialog to the
Adobe dialog's actual rect; Wine executes what it is asked. The OS width only
grows because the Adobe dialog cannot be narrower than ~760-768 here.
Hypothesis (unproven): on Windows the Adobe dialog's minimum width (from its
WM_GETMINMAXINFO, likely font/DPI dependent) is not larger than the OS
dialog's width, so the round trip keeps the size. Next: log the Adobe
dialog's WM_GETMINMAXINFO answer; compare with Windows only if needed.
Wine 34134 c5 (published earlier) says cause unknown; do not post again
until the minimum-size question is answered.

## Minimum sizes (2026-11-08 19:50)

WM_GETMINMAXINFO answers logged with the prefill proxy's DLLMGR27_DEBUG
(version.dll entry): the OS dialog (#32770) reports min 604x602 = its initial
size (comdlg32), the Adobe dialog never answers a WM_GETMINMAXINFO during the
toggle. So 760 is the width Adobe's code chooses itself, not a clamp; the 768
in Wine's calc_winpos trace is the same request in window-rect terms (the X
sizes are 1520 = 760 x 2 physical for both later states).

Status: Wine executes Adobe's explicit MoveWindow of the OS dialog to the Adobe
dialog's rect; no Wine defect is shown. Whether Adobe's code does the same on
Windows cannot be derived from Wine traces (no reverse engineering of
Photoshop). Deciding needs a real Windows run of the same three steps (owner
machine/VM or a Windows CI job installing the CS2 trial).

## Next: Windows CI comparison (owner decision 2026-11-08)

Do it as a Windows job in this repo (next to first-open.yml): download the
CS2 trial installer **from the Wayback Machine, never from Adobe in CI**
(owner: do not load Adobe's servers):
https://web.archive.org/web/20240522171734/http://download.adobe.com/pub/adobe/photoshop/win/cs2/Photoshop_CS2.exe
and verify SHA256 919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea
(345,068,035 bytes); cache it with actions/cache so reruns do not download
again. Unzip it
(identical to the WinZip SFX output), install the trial unattended (owner
approved the trial EULA; no serial), then drive File > Open > Use Adobe
Dialog > Use OS Dialog with UI Automation and record the "Open" window rect
after each step with a small EnumWindows probe (tests/wine/winstyles.c style).
Compare with the Wine numbers above. Expect several blind iterations on the
installer automation; keep each in small commits.

## Windows CI execution started (2026-11-08, codex-debian-8c42)

Issue35 claimed under the multi-agent protocol. Task-specific manual workflow
`ps35-windows.yml` first inspects the verified Wayback archive's public MSI
Property/Control/ControlEvent tables and the Windows runner desktop. Serial/key
property values are redacted. No installer properties are guessed and no serial
is entered. The `measure` implementation follows this inspection; it is not
currently a completed comparison. No WineHQ comment is authorized by this task.
This workflow is specific to35, not a project-wide requirement to run in CI.

### CI flow checkpoint: source inspection in progress

First inspection run: https://github.com/unxed/dllmgr/actions/runs/42532984784 .
At23:04UTC it remained in the pinned Wayback download, before any installation
or measurements. The next increment adds a source-free `stage=probe` so public
Win32/UIA compilation, desktop screenshots and script parsing can be checked
without waiting for or duplicating the345MB download. `ps35-uia.ps1` records
outer/client rectangles, DPI and HWNDs; missing named UIA buttons after two
attempts stop with screenshots/trees rather than guessed mouse coordinates.
The helper is pending its first Windows probe; no comparison result yet.

Source-free run42533552247 passed on real Windows: interactive desktop,
DPI96, compiled public window probes, UI Automation tree and screenshot.
Probe metadata and artifact checksum: `windows-ci/probe-42533552247.json`.
The initial archive download remains pending; no installed-CS2 measurement yet.
Cache key is the exact source SHA256, shared between task runs on main; save
occurs immediately after successful hash verification and before MSI inspection
or installation. `stage=probe` skips both archive restore and download.

A concurrent main update rejected one expected-SHA ref move. An early probe
dispatch then returned422 because the new stage was not yet published; no run
was created. The publish loop was corrected to confirm success before dispatch,
re-read main and retry without force. Preserve that ordering in future sessions.

Inspection42532984784 succeeded: pinned Wayback bytes/hash verified and cache
saved before MSI work. Public Control/ControlEvent metadata identifies
`UNITYSELECTION=TRYOUT` as the normal trial radio path; `ACCEPTEDEULA=1` is
already a package default. Vendor UI assigns its own trial identifier internally;
no serial value is exported or passed by our script. Selected metadata only is
in `windows-ci/trial-mode-public-msi-metadata.json` (full RTF/EULA omitted).
Next: try normal `/qn` with the trial flag; if that refuses, drive the stock
wizard via UIA. Do not invent a serial or bypass an activation/expiry prompt.

### Measurement implementation

`stage=measure` uses normal `msiexec /qn` with UNITYSELECTION=TRYOUT and no
serial input; nonzero install exits fall back to the stock wizard's trial radio
through UIA. Raw MSI logs stay outside the artifact; license/serial-related
lines are removed before export. Installed state and EXE hash are required
before startup. The main menu, three Open states, outer/client sizes, DPI,
HWNDs, screenshots and UIA trees are captured. Activation/expiry barriers or
two failed named-button searches stop for review. This implementation is
pending its first real CS2 Windows run; the source-free probe alone does not
validate the installer or the dialog transitions.
