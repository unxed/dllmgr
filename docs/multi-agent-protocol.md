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
2. #36 leftover: faint 1 px line at the splash edge; compare with Windows
   (can share the Windows CI job of item 1 — coordinate in the issue).
3. #36 delivery: ship the version.dll prefill proxy for Photoshop.exe as a
   dllmgr recipe (binary from CI, not local builds).
4. Deferred installer bugs from docs/sandbox-findings.md: F13/F14 (MSI final
   dialog texts all "&Finish", msiexec 0x6a6 crash), F11/F12 (MSI dialogs
   not DPI-scaled), F9 (EULA letter spacing).
5. (#34 TopPlan dropped by the owner: no installer, not a showcase.)

FastStone queue: #27 every-launch-path follow-up
(docs/tasks/27-every-launch-path.md; delivered in runtime v3, waits for
the owner's retest), then #39, then "detailed output" for `dllmgr status/run/
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
