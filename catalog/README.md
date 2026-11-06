# dllmgr catalog

The catalog is a set of Markdown files in this directory. One file is one
entry. The YAML frontmatter at the top of the file is read by the client; the
prose below it is for people and is rendered by GitHub. There is no backend and
no account: entries arrive through pull requests to this repository, and CI
compiles the frontmatter into `index.json`, the file the client downloads.
The same model is used by the f4 PlugRing catalog.

The catalog carries source, not binaries. A fix is a patch with its sha256 and
a build recipe. A binary may be listed as an option; it must be built by CI from
that source, and the entry gives its checksum.

## Layout

```
catalog/
  fixes/<tracker>-<number>.md        one file per bug, for example winehq-59609.md
  variants/<dll>-<provider>-<version>.md   whole-DLL alternatives
  bundles/<program>-all.md           a composition of fix IDs
  index.json                         compiled by CI, do not edit by hand
```

Fixes are catalogued by bug, not by program. DLLs are a field of an entry, not a
directory level: one bug can need several modules. The client finds entries by
DLL name or by program name through `index.json`.

Trackers: `winehq` (WineHQ Bugzilla, `https://bugs.winehq.org/show_bug.cgi?id=N`).

## Submitting an entry

1. Fork this repository.
2. Add one file: `catalog/fixes/<tracker>-<number>.md` or
   `catalog/variants/<dll>-<provider>-<version>.md`. Fill in the frontmatter
   (fields below) and describe the entry under it.
3. Run `go run ./cmd/dllmgr-catalog check catalog`, then
   `go run ./cmd/dllmgr-catalog build catalog` and include the updated
   `catalog/index.json` in the pull request.
4. Open a pull request. CI repeats the check and fails if `index.json` is not
   the compiled form of the entries.

## Kind `fix`

A source patch for one bug.

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `<tracker>-<number>`; equals the file name without `.md` |
| `kind` | yes | `fix` |
| `title` | yes | the bug title |
| `bug` | yes | URL of the bug (http or https) |
| `dlls` | yes | modules the patch changes, lower case, without `.dll`; non-empty list |
| `patch` | yes | https URL of the patch (unified diff) |
| `patch_sha256` | yes | sha256 of the patch, 64 lowercase hex characters |
| `license` | yes | SPDX identifier |
| `programs` | no | exe names known to be affected, for search |
| `wine` | no | Wine tags the patch is known to apply to, such as `wine-11.0` |
| `recipe` | no | how to build the modules from the patch |
| `binaries` | no | URL of CI-built binaries (release page) |
| `evidence` | no | URL of the CI run or reproducer that shows the effect |
| `authors` | no | list of names |
| `ai_assisted` | no | `true` if an AI agent wrote the change |
| `funding` | no | URL of a bounty or donation page; dllmgr only shows it |

## Kind `variant`

A whole module, not tied to one bug: the module of another Wine release, or a
third-party library. The catalog does not re-upload Wine DLLs; `fetch` points to
the official upstream archive. Microsoft DLLs are not accepted. A third-party
variant needs an open `license` and a `source`.

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | `<dll>-<provider>-<version>`, underscores of the dll name written as `-`; equals the file name without `.md` |
| `kind` | yes | `variant` |
| `dll` | yes | module name, lower case, without `.dll` |
| `provider` | yes | for example `wine`, `cc580` |
| `version` | yes | provider's version, for example `11.0` |
| `arch` | yes | for example `i386`, `x86_64` |
| `license` | yes | SPDX identifier |
| `source` | yes | http(s) URL of the source |
| `sha256` | yes | sha256 of the module file as extracted, before unmarking |
| `title`, `summary` | no | display text |
| `file` | no | file name in the slot, if it differs from `<dll>.dll` |
| `slot` | no | `system` or `sxs:<assembly>` |
| `fetch` | no | where to download from: `urls` (https, non-empty), `sha256` (of the archive), `format` (`deb`, `tar.xz`, `tar.zst`, `raw`), `member` (glob with exactly one match; required unless `raw`) |
| `fixes` | no | ids of fixes already contained in the variant |
| `authors` | no | list of names |

## Rules enforced by `dllmgr-catalog check`

- The file starts with a `---` line, the frontmatter, and a closing `---` line.
- `id` matches `^[a-z0-9]+-[a-z0-9.-]+$` and equals the file name without `.md`.
- `kind` is `fix` or `variant` and matches the directory (`fixes/`, `variants/`).
- All required fields of the kind are present and non-empty.
- Unknown fields are an error, including fields of the other kind.
- Fix: the id is `<tracker>-<number>` with a known tracker; for `winehq` the
  `bug` URL names the same number. `bug` is an http(s) URL, `patch` an https
  URL, `patch_sha256` is 64 lowercase hex characters, `dlls` has no duplicates.
- Variant: the id is `<dll>-<provider>-<version>`; `source` is an http(s) URL,
  `sha256` is 64 lowercase hex characters, `fetch` follows the table above.
- Optional URL fields (`binaries`, `evidence`, `funding`) are http(s) URLs.
- No two files use the same id.
- `index.json` equals the output of `build` (checked in CI).

`index.json` is a JSON array sorted by `id`. Each element holds the frontmatter
fields of the entry and `path`, the file path relative to `catalog/`.

## Kind `bundle`

An application selection built from existing fixes. Fields: `id`, `kind: bundle`,
`title`, non-empty `programs` and `fixes` lists, and optional `wine` tags.
References must resolve to catalog fixes and cannot repeat. Bundle IDs are not
Wine bug IDs. The installer must compose patches for shared modules and retain
one original uninstall baseline.

## Applicability for automatic fixes

An installable application bundle has an `application` ID such as
`faststone` and explicit `profiles`. Each profile records the application
`version`, exact `exe_sha256`, `wine` tag, `host_arch` and `prefix_arch`.
The hash identifies the measured executable, including its PE architecture.
Profiles can cover separate app builds and hosts as evidence becomes available.
`programs` is a discovery hint.

Keep published recipes, applicability and source/asset references in the
dllmgr catalog so the CLI and GUI share one resolution contract.
[fix-it-in-wine](https://github.com/unxed/fix-it-in-wine) owns the agent
workflow, diagnostic helpers and research writeups. It can propose a patch
and recipe through a dllmgr pull request. A recipe link points to the
dllmgr bundle page.
