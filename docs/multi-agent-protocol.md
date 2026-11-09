# Several agents on this repo at once

Applies when more than one agent works here concurrently, including vague
orders like "fix things!" or "fix Photoshop CS2!". The goal: no two agents
on the same problem, no clobbered files, no shared machines resources.

## 1. Pick an identity

`AGENT_ID` = short unique name, e.g. `claude-cloud-1a2b` or `cc-laptop-3f`
(tool + host + 4 random hex). Use it in claims, commits' body
(`Agent: <id>`), branch-free work notes and resource names.

## 2. Claim before working (GitHub issues are the lock)

1. List open work: `gh issue list -R unxed/dllmgr --label claimed` and the
   area's checkpoint (docs/photoshop-handoff.md "Sandbox session
   checkpoint", docs/handoff.md).
2. Pick ONE unclaimed issue. "Fix Photoshop CS2" means: take the next
   unclaimed item of the CS2 queue below; never all of them.
3. Claim it: add label `claimed` and comment
   `claim: <AGENT_ID> <one-line plan> (lease 3h)`. If no issue exists for the
   task, open one first and claim it.
4. Re-read the issue after claiming: if another `claim:` comment appeared
   before yours without a `release:`, the earlier one wins; withdraw with
   `release: <AGENT_ID> lost race`.
5. Lease: comment `heartbeat: <AGENT_ID> <status>` at least every 3 h of
   work. A claim with no heartbeat for 3 h is stale; another agent may take
   it with `takeover: <AGENT_ID> (stale claim of <old id>)`.
6. Finish with `release: <AGENT_ID> <result + commits>` and remove the label
   (or close the issue if the owner's criteria are met; the owner closes
   tracking issues like #31).

Never work on a claimed issue of another agent; if blocked by it, comment
there and pick something else.

## 3. Shared files: append, rebase, never force

- Push small commits to `main` right away (AGENTS.md). On rejection:
  `git pull --rebase` and push again; never `--force`, never rewrite
  history, never revert another agent's commit (ask the owner).
- Shared logs are append-only: docs/sandbox-findings.md (take the next F
  number after rebasing; renumber yours if it collides), area checkpoints
  (add a dated section, do not rewrite others'), experiments/<topic>/
  (one directory per issue; you own the ones you created).
- Single-owner files, change only while holding the matching claim:
  scripts/private-runtime.json (runtime pin), patches/*.patch that are part
  of the runtime build, .github/workflows/app-isolation.yml.

## 4. Machine resources

- Displays: one Xvfb display per agent, `STAND_DISPLAY=:<N>` with N in
  100-199 derived from AGENT_ID (e.g. 100 + first byte of its sha256 % 100);
  check `/tmp/.X11-unix/X<N>` is free first.
- Prefixes and work dirs: `$STAND_DIR=<base>/<AGENT_ID>/...` only; never
  touch another agent's prefix, the owner's ~/.wine or prefix110.
- wineserver: only `wineserver -k` with your own WINEPREFIX set.
- CI: dispatch your own runs; never cancel or re-run another agent's run.
  Releases: one agent at a time, holding the claim of the issue being
  shipped; publish via publish-runtime.yml, then pin.

## 5. Photoshop CS2 queue (take from the top, unclaimed only)

Kept in sync by whoever finishes an item (state on 2026-11-08):

1. #35 Windows CI comparison of the Open dialog (plan in
   experiments/ps35-open-dialog/README.md; Wayback installer only).
2. #36 polish (owner retest 2026-11-09, experiments/photoshop-splash/README.md):
   1 px outline, stale grey frame when the main window is minimized (the
   white strip under it was the owner's screenshot tool, not Photoshop); first capture how Windows renders the
   splash (Windows CI job of item 1), then decide the fix (Opus suggested).
3. #36 delivery: ship the version.dll prefill proxy for Photoshop.exe as a
   dllmgr recipe (binary from CI, not local builds).
4. Deferred installer bugs from docs/sandbox-findings.md: F13/F14 (MSI final
   dialog texts all "&Finish", msiexec 0x6a6 crash), F11/F12 (MSI dialogs
   not DPI-scaled), F9 (EULA letter spacing).
5. (#34 TopPlan dropped by the owner: no installer, not a showcase.)
6. #43 startup UX: focus stealing fixed in the runtime (dllmgr-43); splash
   not minimizing fixed in the version.dll proxy (adopt as managed transient,
   experiments/ps-focus/README.md). Both ship with PS-3.
6a. #41 R6025 pure virtual call when closing an image (owner report,
   not reproduced yet; may lose unsaved work: rank high).
6b. #44 tiny custom cursors at 192 DPI: fixed in winex11
   (patches/dllmgr-44.patch, in the next runtime build; probe
   tests/wine/cursor-scale.sh). Waits for a runtime release + owner retest.
6c. #45 menu artifacts: reproduced under Muffin with stock Wine (with and
   without the proxy), gone on the private runtime (60721 mechanism):
   docs/tasks/45-menu-black.md. Delivered by PS-3.
6d. WineHQ bugs of later Photoshop versions (owner, 2026-11-09): list the
   open Bugzilla bugs for Photoshop CS3..2024, check each on CS2 (stand,
   Muffin); the ones that reproduce are fixed like our own bugs and get a
   comment there (docs/upstream-outbox.md).
7. (now urgent: delivers #43, #44, #45) PS-3 recipe `dllmgr fix photoshop-cs2`: install the version.dll prefill
   proxy (#36 splash) with scripts/prefill-proxy.py, binary built by CI
   (add `build.sh version` to app-isolation.yml packaging like msimg32).

FastStone queue: #27 every-launch-path follow-up
(docs/tasks/27-every-launch-path.md; delivered in runtime v3, waits for
the owner's retest), then #39 (reproduced, focus mechanism:
experiments/faststone-esc/README.md), #40 (hidden Esc confirmation), then "detailed output" for `dllmgr status/run/
uninstall faststone` like `fix` (owner, 2026-11-09: say what exactly is
downloaded, verified, changed and where) (Esc ignored during startup
until the first paint; owner report 2026-11-08), owner retests listed in
docs/handoff.md.

Photoshop 2024 queue: #38 shim works (patches/dllmgr-38); next is the entry
DLL of Photoshop.exe (needs `objdump -p` from a user), then a recipe.

## 6. Talking to the owner

One agent should not flood the owner: report in your claimed issue; send a
short chat summary only when a result is ready or you are blocked. Questions
that block several agents go into one issue comment the others can see.

## 7. Suggested model class per task (suggestion, not a rule)

State 2026-11-09. Any agent may take any item; this only says where a
stronger model is likely to pay off. If an agent finds a task harder than
expected, it records what it learned and leaves the rest for a stronger model.

Fits a mid-size model (Sonnet class), plans and traces are in the repo:
- PS-3 `dllmgr fix photoshop-cs2` (CI-built version.dll proxy, install with
  scripts/prefill-proxy.py, like the FastStone trampoline).
- Detailed output for `dllmgr status/run/uninstall faststone` (like `fix`).
- #39: sample FastStone's main thread in the ~1-2 s gap before
  TFullScreenWindow, time the same span on the Windows runner
  (experiments/faststone-esc/README.md).
- #40: hidden Esc-exit confirmation (stacking/owner vs Windows).
- PuTTY 57513: bisect PuTTY's startup IME calls in keylog.exe
  (experiments/putty-57513/README.md).
- #41: reproduce R6025 on close on the stand; #35 Windows CI comparison.

Suggested for a strong model (Opus class):
- Far: design and Wine conhost patch for win32-input-mode (docs/console-apps.md
  "Route comparison", accepted by the owner) and its private-runtime delivery.
- Any fix that must live inside Wine (win32u/winex11/imm32/msi) and its
  delivery, e.g. if #39/#40/57513 end up there.
- Mechanism analysis once a mid-size agent has a narrowed reproducer.
