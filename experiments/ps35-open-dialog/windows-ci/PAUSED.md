# Task35 paused: resume here

Owner requested save and pause at2026-11-09 00:30CET (2026-11-08 23:30UTC).
Agent: codex-debian-8c42. Issue35 is unfinished; claim released at pause.
No Windows Open-dialog rectangles exist. Do not close the issue or conclude
Windows matches/differs from Wine. No WineHQ publication was made.

## Completed checkpoints

- 874af47: task-specific Windows workflow and pinned Wayback MSI inspection.
- 0a29e72: source-free public Win32/UIA/desktop probe.
- 7aaf5a8: successful inspection/probe evidence and verified source cache.
- 1d2a365: first measured trial install/controller implementation.
- 55fc18a: remove unsupported managed LegacyIAccessiblePattern fallback.
- 9a79743: identify actual RichEdit20W fields, public WM_SETTEXT fallback,
  Windows PowerShell5.1, UIA supported-pattern diagnostics.

Runs: inspect42532984784 SUCCESS; probe42533552247 SUCCESS;
measure42534239661 FAILURE; measure42534500556 FAILURE;
measure42534865330 CANCELLED for the owner's pause. Its artifact13638857501
was downloaded and selected diagnostics permanently saved next to this file.
Original full artifact retention14days; manifest/checksum retained. No Adobe
binaries, raw trial state, serial values or credentials are committed.

## Source cache (already implemented and actually reused)

Stable main-branch Actions cache key:
`ps35-cs2-919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea`.
Cache payload runner.temp/ps35-download contains only the exact345068035-byte
installer. First pinned Wayback download took about7minutes; subsequent
measured jobs restored cache and rechecked full size/SHA without downloading.
Cache saves immediately after verification, before installer/test work. No
Adobe download fallback. Source URL and hash are in inspection/source records.

## Last known Windows state

Runner Windows Server2025 /10.0.26100, interactive1024x768 desktop, DPI96.
Normal trial path proven by public MSI Control/ControlEvent/RadioButton rows:
UNITYSELECTION=TRYOUT. Vendor UI assigns its bundled trial identifier internally;
our code does not read, export or pass a serial. /qn consistently returned1603
at CA_CheckPersErr. The stock GUI fallback displayed the normal trial choice
with the serial field disabled. Its two enabled identity controls are
RichEdit20W, reported as UIA Pane rather than Edit; available patterns may be
empty. Named standard Button HWNDs can accept documented BM_CLICK.

Third attempt filled synthetic identity fields using ValuePattern or public
WM_SETTEXT, then reached the page "Required fields are empty", naming User
Name and Serial Number. See attempt3-install-wait*-uia.json and the cropped
reviewed installer screenshots. No installed.json/comparison.json exists.
The reason is unknown: do not assume an actual serial is needed, nor bypass
this page. Review the filled-field screenshot, normal input notifications and
trial radio path first; if ordinary trial really requires a serial/activation
or is expired, stop and ask the owner as PS-1 requires. Do not supply a key.

The batch loop did not fail fast on this known error page and waited blindly
until the user requested cancellation. This is a controller-flow problem to
address before another long unattended run. Do not rerun identical automation
without inspecting the retained evidence.

## Unvalidated live CI draft, not dispatched

Branch: session/codex-debian-8c42-ps35-live-draft
Commit:962cdb2a0e5ad2ff338c471f5ee53f1980db2d80
Files:.session-lab/lab.py, .session-lab/README.md; temporary replacement of
ps35-windows.yml on that branch only. Main's task workflow remains unchanged.

It ports the earlier task37 HTTPS command-branch transport to native Windows
(taskkill owned children, PowerShell screenshots, credential-free child env).
Only Python syntax was checked. Windows behavior is NOT verified. The draft
passes PS35_KEEP_UI but the measurement script does not yet implement it;
review that, cleanup and encoding before relying on retained windows. No live
session bus/run exists for this draft. Do not merge it or adopt it as a
project-wide CI rule. The owner scoped this method to this task/session.

## Resume order

1. Read current AGENTS.md, multi-agent protocol, PS-1 card and issue35;
   check claims and claim35 only if free. Refresh main without overwriting
   other agents. Parent issue31 is owner-managed.
2. Read this checkpoint and all three failed/cancelled attempt records.
   Inspect the last artifact before any further installation. Cache is ready.
3. Make error pages/timeouts observable; consider the unvalidated live bus so
   the same Windows runner can be inspected without a fresh install per action.
   Do not invent coordinates, serials, activation workarounds or vendor patches.
4. Only after normal trial install is verified, capture OS -> Adobe -> OS Open
   rectangles/client sizes/DPI/HWNDs and screenshots through public APIs/UIA.
   Two missing named-button attempts require saved UIA trees and owner escalation.
5. Publish measured table in issue35 and its README. Compare within-OS width
   growth, accounting for Wine192DPI vs Windows96DPI. No WineHQ post without
   explicit approval. No existing bug fix or comparison verdict is completed.

All own measured runs are stopped; no runner/prefix lease remains. The older
Debian/TCG prefix and task37 Linux CI results are different baselines and must
not be substituted for this missing Windows measurement.
