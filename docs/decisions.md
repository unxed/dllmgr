# Decisions

A log of decisions that shape dllmgr. Each entry gives the date, who decided,
the decision and the reason. Entries are not rewritten; a later decision that
replaces an earlier one says so.

## D1 — The catalog lives in this repository, in PlugRing's model

- Date: 2026-11-06
- Decided by: owner
- Decision: the catalog is `catalog/` in this repository, built the way the f4
  PlugRing catalog is: one entry is one Markdown file with YAML frontmatter for
  the client and prose for people; CI compiles the frontmatter into the index
  the client downloads; entries come through pull requests; there is no
  backend; the catalog carries source, not binaries.
- Reason: a proven model with no server to run, review by pull request, and the
  same shape across the owner's projects.

## D2 — Fixes are catalogued by bug, not by program

- Date: 2026-11-06
- Decided by: owner
- Decision: one file per bug, `catalog/fixes/<tracker>-<number>.md`. Tracker
  `winehq` is WineHQ Bugzilla, for example `catalog/fixes/winehq-59609.md`.
- Reason: a bug is the stable identity of a fix. One program can hit several
  bugs and one bug affects several programs; the program is a searchable field.

## D3 — DLLs are a field of an entry; whole-DLL alternatives are a second kind

- Date: 2026-11-06
- Decided by: Claude (agent), at the owner's request to decide how DLLs fit into the catalog
- Decision: `dlls` is a field of a fix, not a directory level. One bug can need
  several modules: 59609 needs comctl32 and comctl32_v6 on Wine 11. The client
  finds entries by DLL or by program through the compiled index. Whole-DLL
  alternatives that are not tied to one bug (a module from another Wine
  release, a third-party library such as cc580) are a second kind of entry,
  `catalog/variants/<dll>-<provider>-<version>.md`.
- Reason: a directory per DLL would split one bug across several places.

## D4 — The catalog carries source; binaries are optional and built by CI

- Date: 2026-11-06
- Decided by: Claude (agent), following D1 (PlugRing carries source) and concept section 19
- Decision: an entry holds a patch (with its sha256) and a build recipe, or for
  a variant a pointer to the upstream archive. A binary may be listed, built by
  CI from that source, with its sha256.
- Reason: source can be reviewed and rebuilt; a changed Wine DLL is LGPL and
  its source must be available (concept §19).

## D5 — Three repositories

- Date: 2026-11-06
- Decided by: owner
- Decision: Marwin is the console runtime; dllmgr is the manager and the
  catalog; fix-it-in-wine is the AI skill.
- Reason: each has its own audience and release cycle.

## D6 — Documentation and tickets in English

- Date: 2026-11-06
- Decided by: owner
- Decision: documentation, issues and tickets are written in English.
- Reason: one language for all contributors and for agents.

## D7 — dllmgr serves Wine and Marwin

- Date: 2026-11-06
- Decided by: owner
- Decision: one catalog and one set of checks serve both targets, Wine
  prefixes and Marwin.
- Reason: the same DLL variants and fixes are useful to both.

## D8 — dllmgr work starts now with iterations 0 and 1

- Date: 2026-11-06
- Decided by: owner
- Decision: work starts with iterations 0 and 1 of the concept (§14).
- Reason: the spike and the static check give the basis for everything else.

## D9 — Exchanging fixes is a design hook

- Date: 2026-11-06
- Decided by: owner
- Decision: exchanging fixes (concept §19) stays a design hook. Hosting and
  payment are undecided.
- Reason: the architecture must allow it, but nothing is planned yet.

## D10 — Automatic application fixes are the default

- Date: 2026-11-06
- Decided by: owner for the product behavior, Codex for applicability and
  upgrade policy.
- Decision: the CLI and GUI share an application-level planner for **Fix**,
  **Fix all** and their reversals. Resolve verified applicability per app
  version, PE machine and Wine version, with optional host constraints.
  Followed apps are reconciled on a manual catalog refresh and upgrade.
- Reason: the user chooses an app or a prefix once. The planner handles
  portable installs, compatibility, composed DLLs and future fixes, while
  preserving originals for rollback. The same commands can be called by a
  distribution's unattended tooling.

## D11 — Recipes live in the dllmgr catalog

- Date: 2026-11-06
- Decided by: Claude (agent), at the owner's request to choose between dllmgr and fix-it-in-wine
- Decision: bugs, patches, module variants, recipes and their applicability are
  catalog data in this repository. fix-it-in-wine keeps the agent workflow, the
  diagnostic tools and research write-ups, and proposes new entries through
  dllmgr pull requests. A shareable recipe link is the recipe's page here.
- Reason: the CLI, the GUI, CI releases and the agent must resolve the same
  data. Two copies would drift; the skill already looks here first (step 1a).

## D12 — A three-primitive data model with tags (proposal)

- Date: 2026-11-06
- Decided by: Claude (agent), pending the owner's review
- Decision: the catalog has three primitives — bug, module, recipe — and
  everything else (documented or not, application, version, architectures,
  Wine version, target system) is a tag. See `docs/data-model.md`.
- Reason: the owner asked for a model simple enough for people, models,
  scripts and administrators, following OpenStreetMap's "few primitives plus
  key=value" lesson. It matches the current files, so adoption is gradual.
