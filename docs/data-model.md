# Data model

Status: proposal for the owner's review, 2026-11-06 (third draft; see D14).

Budget: no more complex than OpenStreetMap's model (three primitives plus
tags), which people, scripts and tools have handled for twenty years. The
budget is borrowed, not the shape. This model fits in **two kinds of file
and one kind of row**.

## Fix: one file per problem

`catalog/fixes/<id>.md`. It says what is wrong, what changes it, and what
proves that the change works.

```yaml
id: dllmgr-14                       # where the problem is described:
bug: https://github.com/unxed/dllmgr/issues/14   # winehq-N = WineHQ Bugzilla
title: "comctl32 v6: report the whole cell as the LVIR_ICON rectangle"
dlls: [comctl32_v6]
patch: https://…/patches/dllmgr-14.patch          # or: module: <a ready DLL>
patch_sha256: 2e63…
evidence:                           # rows; see "Environment" below
  - {check: faststone85.sh browser, exe_sha256: 05c8…, wine: wine-11.0,
     host_arch: x86_64, prefix_arch: win64, dpi: 192,
     without: fail, with: pass, run: https://github.com/…/runs/42256224744}
```

- Documented in Wine or not is only the id prefix: `winehq-59609` or
  `dllmgr-14`. Filing upstream renames the file.
- The change is a source `patch`, or a whole replacement `module` (a DLL from
  another Wine release, cc580). Same file kind either way.
- Prose below the frontmatter is for people; scripts never read it.

## Recipe: one file per application selection

`catalog/bundles/<id>.md`. The fixes to install together, and where they are
known to work.

```yaml
id: faststone-all
application: faststone
fixes: [winehq-48872, winehq-48874, winehq-59251, winehq-59609, dllmgr-14]
when:
  - {exe_sha256: 05c8…, wine: wine-11.0, host_arch: x86_64, prefix_arch: win64,
     release: faststone-v2}
```

## Environment: one kind of row

A flat `key: value` row: `exe_sha256`, `wine` (or later `target: reactos`),
`host_arch`, `prefix_arch`, `dpi` when it matters, plus what the row is for
(`release` in a recipe; `check`, `without`, `with`, `windows`, `run` in
evidence). The same keys mean the same thing everywhere, so matching "my
system" against a recipe or against a fix's evidence is one comparison.

## What falls out of it

- **Install** (administrator, script): find the recipe, match the user's row
  against `when`, compose the patches per module, build once or download
  `release`, install in one transaction with a byte-exact undo. If nothing
  matches, say which key differs.
- **Trust**: a fix is proven for an environment when its evidence has
  `without: fail, with: pass` there and `windows: pass` for the same check.
  A recipe's `when` should only list rows every one of its fixes has proven.
- **WineHQ Bugzilla gate**: the same three results plus a visual check in the
  real application.
- **Agent**: read one fix file top to bottom; add a row or a fix. A new kind of
  file needs an owner decision.

## Rules

- One fact in one place: fix lists only in recipes, checksums next to their
  files, release tags only in `when` rows.
- `catalog/index.json` is generated, never edited.
- Keys are a closed list checked by the validator: a misspelled
  applicability key must fail, not silently widen a recipe.

## Gaps against the current catalog

1. `evidence` rows do not exist yet; the results are in CI logs and
   `docs/faststone.md`. Next step: add rows to the five FastStone fixes.
2. Recipes call `when` `profiles`; rename together with step 1.
3. `catalog/variants/` holds whole-module changes separately; they can become
   fix files with `module:` when the first one is used by a recipe.
