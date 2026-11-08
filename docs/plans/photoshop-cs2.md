# Photoshop CS2 task cards

Context: docs/photoshop-handoff.md (sandbox checkpoint), issue #31.

## PS-0 (#31) Bugzilla audit: one verdict per row of docs/photoshop-wine-audit.md

Executing agent, in this order: group A, then B, then C; D and E last (they
are reading-only and can be batched 10 rows per commit).
Per bug:
1. Read the whole bug (all comments; attachment descriptions; linked bugs).
   Determine the Photoshop version. If later than CS2 -> verdict
   `skipped: later version X`; if not about Photoshop -> `skipped: not
   Photoshop`. Never assume an unknown version is later: find it or mark
   `insufficient data`.
2. A/B/C rows: write the CS2 reproduction steps into the row's notes, run
   them on the stand (STAND_WM=metacity unless the bug is WM-specific; then
   also Muffin), CS2 installed by scripts/sandbox-install-cs2.sh. Separate
   unpacker / installer / application. Judge by X pixels or exact text.
3. Fill the Verdict cell; one commit per bug (A/B/C) or per 10 rows (D/E).
4. Reproduces -> open a dllmgr issue "Photoshop CS2 / Wine N: ..." and stop
   there: mechanism and fix design go to Opus (send reproducer + logs).
5. Wine comments: draft words-only text in docs/bugzilla/ and the feedback
   ledger (docs/bugzilla/submissions.json, status `prepared`); never post
   yourself; never repeat already published comments (#31 lists them).
Known shortcuts: 53571 is probably sandbox finding F14 (same installer
step); 57715 (Illustrator) shares the #36 mechanism - record only.
Stop and ask if: a bug needs hardware (tablet, scanner), a network service or
a Windows license beyond the CS2 trial.

## PS-1 (#35) Windows CI: Open dialog sizes on real Windows

Goal: three window rects on Windows for File > Open, Use Adobe Dialog, Use OS
Dialog, to compare with Wine (OS 604x602 -> Adobe 760x602 -> OS 768x602,
logical; experiments/ps35-open-dialog/README.md).
Inputs: Wayback installer URL + SHA256 (that README); windows-latest runner.
Steps:
1. Workflow `ps35-windows.yml` (workflow_dispatch). Cache the installer
   (actions/cache, key = SHA256). Download only from the Wayback URL.
2. `Expand-Archive` does not read SFX; use `7z x Photoshop_CS2.exe` (7-Zip is
   on the runner). Verify `Photoshop CS2/Setup.exe` exists.
3. Install unattended. Try first: the MSI inside the unpacked tree with
   `msiexec /i "<msi>" /qn /l*v install.log` plus trial properties; find
   property names by reading the MSI tables with PowerShell
   (WindowsInstaller.Installer COM, `Property` table). Clean-room reverse
   engineering is allowed where needed (AGENTS.md). If /qn refuses, fall back
   to UI Automation of the same GUI path as scripts/sandbox-install-cs2.sh.
4. Start Photoshop.exe, wait for the main window (UIA, class "Photoshop"),
   then File > Open by UIA menu invoke; find "Use Adobe Dialog" by button
   name, then "Use OS Dialog". After each step record GetWindowRect of the
   top-level "Open" window (PowerShell Add-Type + user32), plus screenshots as
   artifacts.
5. Post the three rects in #35; add them to the README table.
Done when: the job prints three rects and uploads screenshots.
Stop and ask if: installation needs a serial/activation or any network login;
the trial expired message blocks startup (do not try to bypass it); UIA cannot
find the buttons after two attempts (send the UIA tree dump).
Traps: runner DPI is 96, the sandbox is 192 — compare logical sizes; first
start of CS2 takes long (wait for the main window, not a fixed sleep).
Decision after: if Windows also ends at 768-ish -> close #35 as app behaviour
(Wine correct); if Windows returns to the original width -> escalate (Opus):
then Adobe reads something whose value differs on Wine.

## PS-2 (#36) faint 1 px line at the splash edge

Goal: decide if the line is a Wine bug or Windows-identical.
Steps: in the PS-1 job, screenshot the splash (it appears for seconds after
start) and crop its border; on the stand capture the same with the version
proxy (experiments/photoshop-splash/README.md). Compare.
Done when: both crops are in the issue with a one-line verdict.
Stop and ask if: the line differs; do not try to fix it inside the proxy.

## PS-3 (#36) ship the splash fix as a dllmgr recipe

Goal: `dllmgr fix photoshop-cs2` installs the prefill `version.dll` proxy for
Photoshop.exe; `uninstall` restores; works on stock Wine.
Design (decided): binary built in CI from patches/dllmgr-27 (`build.sh
version`), published as a release asset with SHA256SUMS; installer downloads
by pinned SHA (pattern: scripts/private-app.py `modules()`), then calls
scripts/prefill-proxy.py apply. No local compile on the user machine.
Steps: CI job building i686 version.dll + SHA256SUMS -> release via the same
publish pattern (extend publish-runtime.yml or a sibling); pin file
`scripts/photoshop-cs2.json`; CLI branch in `dllmgr` for fix/uninstall/status
photoshop-cs2; unit tests with a fake registry (tests/test_prefill_proxy.py
pattern); stand test: splash without white (ps-splash-shots.sh) and full UI
after 30 s looks normal (palettes, no 2x copies).
Stop and ask if: Photoshop.exe is not found automatically in the prefix
(ask the owner how to locate it; do not scan the whole disk).

## PS-4 deferred installer bugs (after PS-1..3)

F13/F14: final MSI dialog texts all "&Finish", then msiexec crashes 0x6a6.
Reproducer first: scripts/sandbox-install-cs2.sh reaches it every time.
Escalate the mechanism analysis to Opus (Wine msi dialog code, custom
actions, RPC binding); an executing agent only collects: `WINEDEBUG=+msi`
log of the final dialog, the MSI Control/ControlEvent rows of that dialog
(PowerShell or msiinfo/msidump from wine), and the backtrace.
F11/F12/F9: collect side-by-side Windows screenshots from the PS-1 job first.

## TopPlan (#34): dropped by the owner 2026-11-08 (no installer; an old
owner report, not a showcase). No further work.
