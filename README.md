# dllmgr

dllmgr is a manager of DLL variants for Wine and for
[Marwin](https://github.com/unxed/Marwin). It comes with a catalog of
libraries and fixes. The manager is written in Go. Its GUI uses
[goWidgets](https://github.com/unxed/goWidgets).

Working name: `dllmgr`. The owner picks the final name.

`dllmgr fix --dry-run` previews the verified recipes for the current prefix.
Normal output shows progress and the result; add `--verbose` for diagnostic
details. Colour follows the terminal and respects `NO_COLOR`.

FastStone AVIF preview: `dllmgr fix faststone-avif`, undo with
`dllmgr unfix faststone-avif`. This experimental x86 WIC codec is separate
from the five-fix recipe; see [scope, supported files and evidence](docs/avif.md).
Corrected Cyrillic Tahoma Bold: `dllmgr fix faststone-fonts`, undo with
`dllmgr unfix faststone-fonts`; see [font scope and evidence](docs/fonts.md).

## How we develop

We follow RUP principles: small atomic increments and immediate delivery to
`main` and the user for testing. Broader testing and refinement follow delivery;
we do not accumulate changes while pursuing perfection. See the
[development policy](docs/development.md).

## What it does

- Installs verified FastStone DLLs in private storage and selects them by the
  full executable path through a private Wine launcher. See [isolation and
  migration](docs/app-isolation.md); AppDefaults alone does not isolate files.
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

- `docs/vision.md`: why this exists and where it goes (the owner's text, with
  editorial notes and a plan table).
- `docs/vendor-kits.md`: the plan for vendors who ship fixed DLLs in their
  own packages (proposal).
- `docs/concept.md`: the concept (targets, model, checks, catalog, CLI, GUI,
  patches, diagnostics, iterations).
- `docs/decisions.md`: the log of decisions (who, when, why).
- `docs/handoff.md`: where the FastStone work stands and what needs a local machine.
- `docs/far3.md`: the Far Manager 3 plan; cloud sessions work on it while GUI work waits (D21).
- `docs/data-model.md`: the catalog data model (fix files, recipe files, environment rows).
- `catalog/`: the catalog. One Markdown file with YAML frontmatter per entry,
  `fixes/` (one file per bug) and `variants/` (whole-DLL alternatives),
  `index.json` compiled from the frontmatter. See `catalog/README.md`.
- `scripts/apply-winehq-59609.sh` and `.github/workflows/release-winehq-59609.yml`: the
  one-step apply and the release build of catalog fix `winehq-59609` (stand-ins until the
  dllmgr CLI exists). Undo with `scripts/undo-winehq-59609.sh`, using the same `WINEPREFIX`.
  Registry output uses the locale's OEM code page, following `unxed/localecp`.
- `cmd/dllmgr-catalog/`, `internal/catalog/`: the catalog validator and index
  compiler (Go). CI: `.github/workflows/catalog.yml`.
- `dllmgr` and `install.sh`: the CLI and per-user installer for the FastStone
  preview. See [installation and recipe links](docs/recipes.md).
- `spike/spike0.sh`: the manual spike of iteration 0.

Planned:

- The Go manager and `gui` subcommand.
- `internal/`: the other packages (PE parser, Wine lookup, state, checks and so on).
- `libs/cc580/`: cc580, comctl32 5.80 written in Bp. Plan:
  https://github.com/unxed/dllmgr/issues/1
- `patches/`: patches over DLLs that cannot be replaced.

## Status

The preview implements `dllmgr fix` (find the programs with recipes in a
prefix and apply them after a yes), `dllmgr fix faststone`,
`dllmgr unfix faststone` and `dllmgr share faststone`. See the [FastStone recipe](catalog/bundles/faststone-all.md)
for the supported configuration and measured results. The planned `fix world`,
subscriptions, unattended updates and GUI are described in the
[CLI and GUI design](docs/concept.md#10-cli).

## License

BSD-3-Clause. See `LICENSE`.

> **Safety correction ([#25](https://github.com/unxed/dllmgr/issues/25)):**
> legacy system/SxS DLL replacement is disabled. FastStone installation uses
> an application-private runtime and launcher. Existing legacy replacements
> must be restored first. Fonts and AVIF remain separate, explicitly
> prefix-wide operations. See [scope and migration](docs/app-isolation.md).
