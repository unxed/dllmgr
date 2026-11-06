# Data model

Status: proposal for the owner's review, 2026-11-06 (second draft, replaces
the tag-centric first draft; see D13).

The model must be readable by a person, an AI agent, a shell script and a
tired system administrator, and still answer hard questions. OpenStreetMap
is the inspiration for the *spirit*: a model that is small, obvious and
composes into something powerful. Its literal shape (points, lines,
polygons, free tags) does not fit this domain and is not copied.

## The one question

Everyone who touches the catalog asks the same thing:

> Will this change make this program work on my system, and what proves it?

The model is built around that sentence. It has three things and one value.

## Problem, change, check — and an environment

| | What it is | Example | File |
| --- | --- | --- | --- |
| **Problem** | Something a program does wrong under Wine | thumbnails overflow their tiles | `catalog/fixes/<id>.md` |
| **Change** | A precise edit that fixes a problem: a source patch, or a whole replacement module | `patches/dllmgr-14.patch` | same file as its problem, or `catalog/variants/<id>.md` |
| **Check** | A program or procedure whose result shows the problem present or absent | `tests/wine/faststone-controls.c --check-label` | listed in the problem file |
| *Environment* | A value, not an entity: the exact program build, the target system and its version, host and prefix architectures, DPI when it matters | `FSViewer.exe sha256 05c8…, wine-11.0, x86_64, win64, 192 DPI` | written inline |

How they relate:

- A problem has an id from wherever it is described: `winehq-59609` (WineHQ
  Bugzilla) or `dllmgr-14` (this repository, no upstream report yet).
  "Documented in Wine" is not a different kind of thing, only a different
  place. Filing it upstream renames the file and keeps the old id as `aka`.
- A change belongs to one problem. The first draft of any fix is one change;
  a competing approach is a second change on the same problem.
- A check produces **evidence**: `check × environment × (without, with) change
  → result`, with a link to the run. Evidence is what makes everything else
  trustworthy:
  - *the problem is real* — the check fails without the change;
  - *the fix works* — it passes with only this change;
  - *nothing broke* — the same check passes on Windows;
  - *it applies to you* — the environment in the evidence matches yours.

  This is also the WineHQ Bugzilla gate (docs/faststone.md): a report is
  allowed once the evidence for its problem has all three of the first rows.

## Recipes are a view

A **recipe** is what a user installs: the changes chosen for one
application. It is not a new kind of fact. It lists problem ids, and its
applicability is the set of environments where every listed change has
passing evidence (plus a visual check in the real application).

```yaml
id: faststone-all
application: faststone
fixes: [winehq-48872, winehq-48874, winehq-59251, winehq-59609, dllmgr-14]
when:                       # environments covered by the evidence
  - exe_sha256: 05c877e5…
    wine: wine-11.0
    host_arch: x86_64
    prefix_arch: win64
    release: faststone-v2   # prebuilt modules for exactly this environment
```

Today `when` is called `profiles` and is written by hand from the CI runs.
Once evidence is recorded in the problem files, it can be computed.

## How each reader uses it

- **Administrator**: `dllmgr fix faststone`. The tool finds the `when` that
  matches, or says which value differs (for example "Wine 11.2, measured on
  11.0").
- **Script**: resolve recipe → problem ids → changes; group patches by
  module; apply them to one pristine tree per module; build once or download
  `release` and check `SHA256SUMS`; install in one transaction with a
  byte-exact undo. (`scripts/catalog_fixes.py`, `select-faststone.py`.)
- **Agent**: read a problem file top to bottom: symptom, cause, change,
  checks, evidence, what is still unknown. Add evidence or a change; never a
  new kind of entity without an owner decision.
- **Wine reviewer**: the problem file plus its evidence table is the report.

## Rules that keep it simple

- One fact in one place. A fix list exists only in its recipe; a checksum only
  next to its file; a release tag only in its `when` item.
- Every file reads on its own. `catalog/index.json` is generated.
- Prose is for people; scripts read only the frontmatter.
- Closed vocabulary. Frontmatter keys are a fixed list checked by the
  validator, because a misspelled applicability key must fail loudly, not
  silently widen a recipe. Adding a key is a one-line change plus a row in
  `catalog/README.md`.

## Gaps against the current catalog

1. Checks and evidence live in CI logs and in `docs/faststone.md` prose. Next
   step: an `evidence` list in each problem file — `check`, `environment`,
   `without`, `with`, `windows`, `run` — filled from the existing runs.
2. `profiles` → `when`, derived from evidence later.
3. `kind: fix`/`bundle` read as problem/recipe; renaming can wait.
4. Not modelled yet, by choice: dependencies between changes (none needed so
   far) and per-Wine-version patch variants (add when a patch first fails to
   apply on another tag).
