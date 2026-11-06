# Data model

Status: proposal for the owner's review, 2026-11-06. The current catalog
(`catalog/`) already follows most of it; the gaps are listed at the end.

The model has to be readable by a person, an AI agent, a shell script and a
tired system administrator. It follows OpenStreetMap's lesson: a few plain
primitives plus free key=value tags beat a perfect schema. Nothing here is
OSM's design; only the principle is borrowed.

## Three primitives

| Primitive | Answers | One file | Identity |
| --- | --- | --- | --- |
| **bug** | What is wrong, and how to change the source so it is not | `catalog/fixes/<id>.md` | `<tracker>-<number>` |
| **module** | Which ready DLL can replace a module as a whole | `catalog/variants/<id>.md` | `<dll>-<provider>-<version>` |
| **recipe** | What to install for which program on which system | `catalog/bundles/<id>.md` | `<app>-<name>` |

Everything else is a **tag** on one of these, not another entity.

- A **documented Wine bug** and an **undocumented bug** are the same primitive.
  The tracker in the id says where it is described: `winehq-59609` lives in
  WineHQ Bugzilla, `dllmgr-14` lives in this repository's issues because no
  upstream report exists yet. Filing it upstream renames the file; the old id
  stays as `aka: [dllmgr-14]`.
- A **fix** is the `patch` of a bug. A bug without a `patch` is still useful: it
  records a symptom and its evidence. One bug normally has one patch; an
  alternative patch is a second bug entry only if it fixes something else.
- An **application**, its **version**, the **host architecture**, the
  **prefix architecture**, the **Wine version** and the **target system**
  (Wine, ReactOS, …) are tag values. They appear in a recipe's `when` blocks
  and as search hints (`programs`, `wine`, `dlls`) on bugs.

## Tags

Tags are YAML frontmatter keys with plain values: strings, numbers, or lists of
strings. No nesting except a recipe's `when` list. Unknown keys are rejected by
the validator so typos cannot hide; adding a key means one line in
`internal/catalog/parse.go` and one row below.

| Key | On | Meaning |
| --- | --- | --- |
| `id`, `kind`, `title` | all | identity, primitive, one-line summary |
| `bug` | bug | URL of the report the id names |
| `dlls` | bug | modules the patch changes (`comctl32`, `comctl32_v6`) |
| `programs` | bug, recipe | exe names, for search only |
| `wine` | bug | Wine tags the patch was built and tested on |
| `patch`, `patch_sha256` | bug | the source change and its checksum |
| `status` | bug | `candidate`, `verified`, `upstream` (merged in Wine), `obsolete` |
| `fixed_in` | bug | first Wine tag that contains the fix; recipes skip it there |
| `license`, `ai_assisted`, `evidence` | bug, module | provenance |
| `fixes` | recipe | ordered list of bug ids to compose |
| `application` | recipe | short name used on the command line (`faststone`) |
| `when` | recipe | list of measured combinations, see below |

## Applicability: `when`

A recipe applies only where it was measured. Each `when` item is a flat set of
key=value conditions, all of which must match; any item may match.

```yaml
when:
  - exe_sha256: 05c877e5…   # the exact program build (also fixes its PE arch)
    version: "8.5"          # for people; the hash decides
    wine: wine-11.0
    host_arch: x86_64
    prefix_arch: win64
    release: faststone-v2   # prebuilt modules for this combination
```

Today this list is called `profiles`. A future `target: reactos` key covers
other NT-compatible systems (issue 13) without a new entity.

## How a script uses it

1. Pick the recipe by `application` or id.
2. Find the `when` item that matches the program's hash, the Wine tag and the
   architectures. No match: refuse, explain which key differed.
3. For each id in `fixes`: skip if `fixed_in` ≤ current Wine; otherwise take its
   `patch`.
4. Group patches by module, apply them to one pristine tree per module, build
   each module once (or download `release` and check `SHA256SUMS`).
5. Install in one transaction; keep the originals for a byte-exact undo.

`scripts/catalog_fixes.py` implements steps 1 and 3 (without `fixed_in` yet);
`scripts/select-faststone.py` implements step 2 for FastStone.

## Rules that keep it simple

- One fact lives in one place. Lists of fixes exist only in a recipe; release
  tags only in its `when` items; checksums only next to the file they check.
- A file is readable without the index. The index (`catalog/index.json`) is
  generated and never edited by hand.
- Prose under the frontmatter is for people: what breaks, why, how it was
  checked. Scripts never parse it.
- A new kind of fact is a new tag first. A new primitive needs an owner
  decision in `docs/decisions.md`.

## Gaps against the current catalog

- `kind: fix` and `kind: bundle` read as "bug" and "recipe" here. Renaming is
  cosmetic and can wait; the directories stay.
- `profiles` → `when`; `status`, `fixed_in`, `aka` are not implemented yet.
- `programs`/`wine` on bundles duplicate the `when` items; derive them instead.
