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
- Accept EULAs only with explicit owner approval (CS2 trial: approved).
- Commit messages in English; talk to the owner in Russian, concise.
- Patches/binaries: CI builds release binaries; private-runtime releases are
  published with .github/workflows/publish-runtime.yml (owner-approved),
  then pinned in scripts/private-runtime.json.
