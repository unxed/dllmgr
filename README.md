# dllmgr

dllmgr is a manager of DLL variants for Wine and for
[Marwin](https://github.com/unxed/Marwin). It comes with a catalog of
libraries and fixes. The manager is written in Go. Its GUI uses
[goWidgets](https://github.com/unxed/goWidgets).

Working name: `dllmgr`. The owner picks the final name.

## What it does

- Sets one DLL for one program. The module can come from another Wine
  release or from a third party, for example cc580.
- Keys the rule by exe name. One rule covers every copy and every version
  of the program in a prefix, installed or portable.
- Applies patches for DLLs that cannot be replaced (DLLs with a unix part
  and the system core).
- Rolls back in one step. Removing a rule restores the prefix byte for byte.
- Checks that the override really took effect: a static import check and a
  check by running the program.
- Collects debug data with presets. The output has a short digest for
  agents and for people.
- Serves two targets with the same catalog and the same checks: Wine
  (prefixes) and Marwin.

## Related projects

- [Marwin](https://github.com/unxed/Marwin) is a light runtime for Windows
  console programs, written in Bp. It is the second target of dllmgr.
- [fix-it-in-wine](https://github.com/unxed/fix-it-in-wine) is an AI agent
  skill "fix my application under Wine". It uses dllmgr to apply, undo,
  verify, collect diagnostics and install patches.

## Layout

Existing:

- `docs/concept.md`: the concept (targets, model, checks, catalog, CLI, GUI,
  patches, diagnostics, iterations).
- `docs/decisions.md`: the log of decisions (who, when, why).
- `catalog/`: the catalog. One Markdown file with YAML frontmatter per entry,
  `fixes/` (one file per bug) and `variants/` (whole-DLL alternatives),
  `index.json` compiled from the frontmatter. See `catalog/README.md`.
- `scripts/apply-winehq-59609.sh` and `.github/workflows/release-winehq-59609.yml`: the
  one-step apply and the release build of catalog fix `winehq-59609` (stand-ins until the
  dllmgr CLI exists). Undo with `scripts/undo-winehq-59609.sh`, using the same `WINEPREFIX`.
  Registry output uses the locale's OEM code page, following `unxed/localecp`.
- `cmd/dllmgr-catalog/`, `internal/catalog/`: the catalog validator and index
  compiler (Go). CI: `.github/workflows/catalog.yml`.
- `spike/spike0.sh`: the manual spike of iteration 0.

Planned:

- `cmd/dllmgr/`: the CLI and the `gui` subcommand.
- `internal/`: the other packages (PE parser, Wine lookup, state, checks and so on).
- `libs/cc580/`: cc580, comctl32 5.80 written in Bp. Plan:
  https://github.com/unxed/dllmgr/issues/1
- `patches/`: patches over DLLs that cannot be replaced.

## Status

The only code so far is the catalog tool (`cmd/dllmgr-catalog`). The manager itself
is not written yet. Work starts with iterations 0 and 1 of the concept
(owner's decision, 2026-11-06).

## License

BSD-3-Clause. See `LICENSE`.
