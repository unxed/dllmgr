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
- Never reverse-engineer proprietary programs (Photoshop, FastStone):
  public APIs, observable behaviour, Wine source only.
- Do not post to WineHQ Bugzilla or other public trackers without the
  owner's explicit approval. Comments on this repo's own issues are fine.
- Accept EULAs only with explicit owner approval (CS2 trial: approved).
- Commit messages in English; talk to the owner in Russian, concise.
- Patches/binaries: CI builds release binaries; private-runtime releases are
  published with .github/workflows/publish-runtime.yml (owner-approved),
  then pinned in scripts/private-runtime.json.
