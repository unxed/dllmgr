# Agents: start here

dllmgr fixes Windows programs under Wine. Before any work read, in order:

1. This file (rules that bind every agent).
2. docs/multi-agent-protocol.md — claim work first; other agents may be
   running on this repo right now.
3. Your environment:
   - console Claude Code / any agent on the owner's machine: docs/console-agent.md
   - Claude cloud sandbox (root, disposable Ubuntu): docs/sandbox-agent-hints.md
4. Task cards with decided designs and stop points: docs/plans/README.md.
5. The area you work on: docs/photoshop-handoff.md (Photoshop CS2),
   docs/handoff.md / docs/faststone.md (FastStone), docs/development.md
   (process), docs/concept.md (architecture), docs/decisions.md.

Rules (owner's, non-negotiable):

- "Commit" / "save to GitHub" from the owner is executed at once, before
  anything else, whatever state the work is in: as WIP, on a branch, or
  behind a switch that keeps it off. Within seconds everything not yet on
  GitHub must be there. Never "one more minute to finish". Owner's command
  always comes first (owner, 2026-11-10).
- Small atomic commits, pushed to `main` immediately, each with its tests and
  doc updates, so work can continue from the repo alone. Never batch.
- Fail fast: missing data, broken build/environment, unclear task -> stop
  and ask the owner; never guess.
- Strict scope: fix what was asked. Problems found on the way go to
  docs/sandbox-findings.md (or the area's findings list) and are fixed last.
- Debug by bisecting large chunks (about half per step), not by micro-steps.
- Never open windows on the owner's desktop or use their default prefix:
  headless stand only (`scripts/sandbox-stand.sh session`), disposable
  prefixes.
- Lawful clean-room reverse engineering of the **target programs**
  (Photoshop, FastStone, ...) is allowed (owner, 2026-11-08): one agent
  studies the binary and writes a plain-text description of the behaviour
  into the repo; another agent implements from that description only. Never
  copy vendor code or disassembly into our code.
- **Microsoft components stay black-box only** (Wine Clean Room Guidelines,
  fix-it-in-wine SKILL.md rule 6): no disassembly, symbols or +relay of
  Windows DLLs; Windows behaviour comes from probes run on Windows (e.g.
  .github/workflows/windows-probes.yml). Code is never sent to Wine; Wine
  gets words-only descriptions.
- General Wine-fixing method and measurement rules live in the
  fix-it-in-wine skill (SKILL.md); this repo keeps project-specific plans.
- Reproduce every owner complaint on the owner's stack first: Linux Mint
  Cinnamon, X11, Muffin (`STAND_WM=muffin`, the stand default). Other WMs
  only as an extra comparison (owner, 2026-11-09).
- **Trap: what the owner sees is not the X screen.** His laptop panel is
  1920x1080, the X screen 3072x1728: Cinnamon's fractional scaling renders
  at 2x and xrandr scales the whole framebuffer by 0.625 to the panel
  (docs/owner-machine.md). Screenshots and the stand show the 2x frame;
  his eyes get it resampled to ~120 DPI. Judge text, thin lines, cursors
  and pixel-exact fixes also after a 0.625 downscale
  (scripts/as-seen.py: xrandr transform 1.6, filter bilinear, verified with
  `xrandr --verbose` on the owner's machine), and keep in mind that HiDPI with fractional scaling
  is common: every case where Wine handles it badly is a WineHQ report
  for docs/upstream-outbox.md (owner, 2026-11-10).
- When a fix lives only in the private runtime (a Wine patch), also look,
  without waiting to be asked, for an in-process workaround (proxy DLL,
  hooks, Win32-only means) that gives the same result on any Wine, and ship
  it if it works; the runtime fix stays the proper one (owner, 2026-11-09,
  after the menu fade-in for #45).
- Upstream ledger: everything we owe a report or comment to (WineHQ, Linux
  Mint, others) goes into docs/upstream-outbox.md the moment it is found,
  so the owner can post in batches; nothing may be lost.
- A bug that shows only with a Linux Mint component (Muffin, Cinnamon,
  ...) also gets a Linux Mint report, with cross links both ways between the
  Mint and WineHQ reports (owner, 2026-11-09).
- Do not post to WineHQ Bugzilla or other public trackers without the
  owner's explicit approval. Comments on this repo's own issues are fine.
- Close an issue yourself as soon as the owner has confirmed the fix (owner,
  2026-11-09), with a one-line comment saying so; do not ask first.
- The owner cannot always run checks by hand: do not wait for him; verify on
  the stand yourself (experiments/photoshop-cs2-e2e/e2e.sh for Photoshop CS2)
  and queue what only he can check.
- Owner, 2026-11-09: close Photoshop CS2 bugs (then the next items of the
  plan) with dllmgr and fix-it-in-wine on your own: how to catch, test and
  fix them is the agent's job. Ask as little as possible; use the stand,
  Windows CI runners for Windows comparisons, and your own judgement.
- Accept EULAs only with explicit owner approval (CS2 trial: approved).
- Commit messages in English; talk to the owner in Russian, concise.
- Patches/binaries: CI builds release binaries; private-runtime releases are
  published with .github/workflows/publish-runtime.yml (owner-approved),
  then pinned in scripts/private-runtime.json.
