# dllmgr: manager of DLL variants for Wine and Marwin. Concept v0.4

Working name: `dllmgr`. The owner picks the final name.
Language: Go. GUI: `github.com/unxed/goWidgets`.
Code, catalog, libraries and patches live in this repository.

## 0. Purpose

The system Wine comes from the distribution repository (Mint 22 gives Wine 9.0).
The user needs to say: "take comctl32 from Wine 11 and enable it **only for
FastStone** (`FSViewer.exe`, installed or portable) in the prefix
`~/.wine`; roll back with one button".
The default experience is `dllmgr fix faststone` or the GUI's **Fix FastStone**
action. Both discover the app and apply a verified, compatible set. The manual
DLL and slot controls remain available under advanced options (§10–11).
The user also needs to publish own DLL implementations (for example cc580,
comctl32 5.80 written in Bp) in a common catalog, so that others install them
the same way.

dllmgr serves two targets: Wine (prefixes) and Marwin (§3).

Non-goals:
- Changing the system Wine.
- Microsoft DLLs (that is winetricks).
- Replacing DLLs that have a unix part, and the system core. These are fixed
  with patches (§16).

How it differs from existing tools. winetricks installs native Microsoft DLLs,
mostly for the whole prefix. Prefix managers let the user choose a version only
for a fixed set of components (DXVK, VKD3D and so on), also for the whole
prefix. dllmgr gives an open catalog of any DLLs, a rule for a given exe, and a
check that the rule really took effect.

## 1. Terms

- **Variant**: one build of a DLL: `dll@provider:version/arch`, for example
  `comctl32@wine:11.0/i386`, `comctl32@cc580:0.1/i386`.
- **Slot**: where the module is loaded from in a prefix. `system` (system32 or
  syswow64, depending on bitness) or `sxs:<assembly>` (a directory in `winsxs`).
- **Rule**: (prefix, exe name, dll, slot) -> variant.
- **Catalog**: the set of Markdown entries (YAML frontmatter plus prose) that
  describe fixes and variants. The main catalog is `catalog/` in this
  repository (§8). There can be several catalogs.
- **Local cache**: the checked DLL files on the local disk, addressed by
  sha256.
- **Mismatch**: a file or a registry value changed outside dllmgr.
- **Entry DLL**: a copy of a builtin leaf DLL with one added import, the patch
  loader (§16).
- **Unmark**: clear the builtin mark of a DLL (F1).

## 2. Verified facts about Wine (rely on them, do not re-check)

Scope correction: historical basename overrides below describe Wine load order,
not application isolation. Current product routing is specified in
[application isolation](app-isolation.md).

Checked against the sources of the tags `wine-9.0` and `wine-11.0`.

- **F1. Builtin mark.** In Wine builtin DLLs, 32 bytes `"Wine builtin DLL"` lie
  right after `IMAGE_DOS_HEADER` (offset 0x40). This is what the loader does
  with such a file (`dlls/ntdll/unix/loader.c`, `load_builtin()`): with load
  order `native` it reports "not found"; with any other order it loads **its
  own** builtin DLL from the installation directory. So a DLL from another Wine
  version is ignored unless it is changed. Solution: zero these 32 bytes
  (unmark). Files marked `"Wine placeholder DLL"` are empty stubs without code.
  We do not accept them.
- **F2. Load order** (`dlls/ntdll/unix/loadorder.c`: `get_load_order`,
  `get_load_order_value`). For each form of the name, the loader checks in
  turn: `WINEDLLOVERRIDES`, then
  `HKCU\Software\Wine\AppDefaults\<exe>\DllOverrides`, then
  `HKCU\Software\Wine\DllOverrides`. Forms of the name: the full path without
  extension (for files from the system directory, just the name), then
  `*name`, then `name`. If there is no override (`LO_DEFAULT`), the builtin DLL
  wins even when a native file is found. The exception is a builtin with the
  PREFER_NATIVE flag. Two consequences: without an explicit override our file
  is normally not loaded. This does not isolate a physically replaced shared
  DLL: another load-order rule can select it in another process. The product
  uses full-image-path private runtime routing; see [#25](app-isolation.md).
- **F3.** With order `native,builtin`, an unmarked file is loaded as native, and
  an untouched marked file still gives the Wine builtin DLL (`load_builtin`
  turns the order into `LO_BUILTIN_NATIVE`). So we always write
  `native,builtin`, never `native`.
- **F4.** When Wine is updated, wineboot (`dlls/setupapi/fakedll.c`:
  `create_dest_file`, `is_fake_dll`) does not overwrite files without the
  builtin or placeholder mark. So our file survives a Wine update and is still
  used. The change of the Wine version must be tracked.
- **F5.** In Wine 9 one comctl32 serves both v5 and v6 (v6 through winsxs). In
  Wine 11 these are two modules: `comctl32.dll` and `comctl32_v6.dll`
  (`dlls/comctl32_v6`, installed in system32). The imports also changed: 11
  added `oleaut32` and the delayed `oleacc`. So "comctl32 from Wine 11" means
  two variants, and for Wine 9 the v6 variant goes to the winsxs slot under the
  name `comctl32.dll`. What FastStone needs exactly is shown by spike I0.
- **F6. Log lines** (`dlls/ntdll/loader.c`):
  `trace:loaddll … Loaded <path> at <address>: native|builtin`. A missing import
  is a WARN in the `module` channel:
  `No implementation for X.Y imported from Z, setting to …`. This needs
  `WINEDEBUG=+loaddll,warn+module`. A missing import does not stop loading;
  the failure comes at the call.
- **F7.** The WineHQ pool
  `https://dl.winehq.org/wine-builds/ubuntu/pool/main/w/wine/` has i386
  packages of Wine 11 for noble: `wine-stable-i386_11.0.0.0~noble-1_i386.deb`,
  `wine-devel-i386_11.21~noble-1_i386.deb` (state on 2026-11-06). The path
  inside a package is found with `find` on `*/i386-windows/<dll>.dll`, without a
  hardcoded prefix.

Hypotheses that spike I0 checks:
- **H1.** comctl32 from Wine 11, unmarked, loads in Wine 9 as native. If there
  is "No implementation", the log shows which functions are missing.
- **H2.** FastStone loads comctl32 from system (v5) or from winsxs (v6). Which
  one it is.
- **H3.** The FastStone bugs we need are really fixed in Wine 11. In the dialog
  of bug 59609 the problem was also reproduced on 11.12, so not everything is
  fixed.
- **H4.** `comctl32_v6.dll` placed in winsxs under the name `comctl32.dll`
  works.

## 3. Targets

A target is the system whose programs dllmgr manages. A target provides:
- (a) the list of its builtin modules and their exports (for the import check,
  §6);
- (b) where a DLL goes for a program;
- (c) how a per-program override is set;
- (d) how the load log is read (for `verify` and `diag`).

**Wine** is the first target. All other sections describe it unless they say
otherwise.
- (a) The builtin DLLs of the target Wine, in `<dll_dir>/<arch>-windows/`
  (§6).
- (b) A slot in a prefix: `system` or `sxs:<assembly>` (§1).
- (c) A registry value
  `HKCU\Software\Wine\AppDefaults\<exe>\DllOverrides\<dll>` (F2).
- (d) The `+loaddll` and `warn+module` lines of the Wine log (F6).

**Marwin** is the second target. It comes when Marwin has a PE loader.
- Marwin reads the per-program rules of dllmgr directly.
- Marwin writes its load log in the line format of Wine's `+loaddll`. So
  `verify` and `diag` work unchanged.
- `dllmgr check --target marwin <dll|exe>` lists the imports that Marwin does
  not export yet. This is a to-do list for Marwin.
- Open: the list of Marwin builtin modules and exports (format and source), the
  directory where a DLL goes for a program, and the location and format of the
  rules file that Marwin reads. They are defined together with the Marwin PE
  loader.

## 4. Model: declarative state and idempotent synchronization

A prefix is described by a set of rules (the desired state) and by the stored
originals. Every action changes the set of rules and calls `reconcile()`.
- Rollback means removing the rule. `reset` removes all rules, and the prefix
  returns byte for byte to its original state.
- Reconcile is idempotent. Persist the transaction intent and originals before
  changing files so a repeated run can recover an interrupted operation.
- "Undo the last" takes the "before" snapshot from `history.jsonl` (snapshots of
  the set of rules before and after each change).

`$WINEPREFIX/dllmgr/state.json` (outside `drive_c`, moves together with the
prefix):
```json
{
  "schema": 1,
  "rules": [{
    "app": "FSViewer.exe", "dll": "comctl32", "slot": "system",
    "variant": "comctl32@wine:11.0/i386", "sha256": "…",
    "wine_at_apply": "wine-9.0 (Ubuntu …)", "exe_paths": ["…"], "added": "…"
  }],
  "subscriptions": [{"app_id": "faststone", "roots": [], "source": "fix"}],
  "originals": {
    "files": {"drive_c/windows/syswow64/comctl32.dll":
              {"sha256": "…", "backup": "dllmgr/backup/<sha256>", "symlink_to": null}},
    "reg":   {"HKCU\\Software\\Wine\\AppDefaults\\FSViewer.exe\\DllOverrides\\comctl32":
              {"absent": true}}
  }
}
```

Algorithm of `reconcile()`:
1. From the rules, build the desired files `slot -> sha256`. If two different
   hashes claim one path, it is an error before any change (a conflict; name
   both rules).
2. Desired registry values: for each rule,
   `AppDefaults\<exe>\DllOverrides\<dll>=native,builtin`. Plus the global
   `<dll>=builtin`, if the builtin DLL of the target Wine has PREFER_NATIVE
   (otherwise all programs pick up our file).
3. For each path in the union of "desired" and "originals":
   - If the file is desired: current == desired -> nothing. Current == original
     (or the original is not stored yet) -> store the original (once) and write
     ours. Otherwise it is a **mismatch**.
   - If the rule was removed: current == ours -> restore the original and forget
     it. Current == original -> forget it. Otherwise it is a **mismatch**.
   - On a mismatch: stop and show what changed and by whom, for example
     `winetricks cc580`. Accepting the current state as the new original needs an
     explicit `--adopt`.
4. The same rules apply to registry values (through the `Registry` interface).
5. Write only through a temporary file in the same directory plus rename. Never
   write through a symlink. If the slot is a symlink (say, into the Wine system
   directory), the link itself is replaced, and its target is stored in the
   original.
6. `state.json` is saved atomically after each successful operation.

Automatic selections persist the canonical app ID, matched installation paths,
their observed versions and PE architectures, and the selected fix IDs and
concrete artifact hashes. Subscriptions are separate desired policy. The app
may be followed even when it has no compatible fix yet. On upgrade, resolve
again against the current installations and catalog. Use a prefix lock and
stage all downloads, compatibility checks and conflict checks before changing
files. Commit interacting rules in one transaction and restore the previous
files, registry values and state on failure. Keep the first original across
all upgrades so unfix still restores it.

## 5. Checks before apply (all before the first change)

- a. **Bitness.** The prefix architecture is the line `#arch=win32|win64` in
  `system.reg`. The bitness of the variant must fit the prefix. If the path to
  the exe is known, it must also match `Machine` in the exe's PE. i386 in win64
  -> `syswow64`, i386 in win32 -> `system32`, x86_64 -> `system32`. x86_64 in
  win32 is an error.
- b. **Replaceability.** The DLL is not in the forbidden list (`ntdll kernel32
  kernelbase win32u user32 gdi32 wow64*`, `*.drv`) and has no unix part: the
  directory of the target Wine has no `<arch>-unix/<dll>.so`, and for variants
  from the wine provider the source archive has none either. DLLs that cannot be
  replaced are not changed. They are fixed with patches (§16).
- c. **Variant file.** A valid PE, the DLL flag, not a placeholder, unmarked.
- d. **Imports** (§6). Regular imports are an error, delayed ones are a
  warning. The strictness is set in the config.
- e. **Slot found.** For `sxs:`, a glob over `winsxs/<x86|amd64>_<assembly>_*`
  must give exactly one directory. Otherwise it is an error with the list of
  candidates.
- f. **Conflicts** (§4, step 1).
- g. **Warnings.** `WINEDLLOVERRIDES` mentions this dll (the variable overrides
  the rule). A global override of the dll with native first. A `*dll` key (it
  overrides the rule for an sxs path).

## 6. Static import check (`check`)

`debug/pe` from the standard library knows only imports by name. We need our own
minimal parser (about 300 lines): imports by ordinal, the delay-import
directory, the export directory (names, ordinals, forwarders).

How each imported DLL is resolved:
1. Another variant from the rules of the same exe.
2. The builtin DLL of the target Wine, `<dll_dir>/<arch>-windows/<dll>.dll`.
3. Otherwise, an error.

Forwarders are followed one step. `api-ms-win-*` are regular files in the
directory of builtin DLLs. The result is "ok" or a list such as
`user32.Foo (import)`, `oleacc.Bar (delay)`. The check does not see Wine's stub
exports or differences in behavior. `verify` catches those.

Finding the target Wine: `wine --version`. Candidates for the directory of
builtin DLLs: `/usr/lib/<triplet>/wine/<arch>-windows`,
`/usr/lib/wine/<arch>-windows`, `/opt/wine-*/lib/wine/<arch>-windows`,
`<realpath(wine)>/../lib/wine/<arch>-windows`, plus the config override
`wine.dll_dirs`. A directory is accepted if it holds `ntdll.dll` with the
builtin mark. If nothing is found, it is an error asking the user to set the
path in the config. Do not guess.

Measured: the regular imports of comctl32 and comctl32_v6 from Wine 11.0 (307
and 384) were all found in the exports of Wine 9.0 from Ubuntu noble (package
libwine 9.0~repack-4build3, i386) on 2026-11-06.

Open question: in Wine's own builds the PE delay-import directory (data
directory 13) is empty. So the descriptors of delay imports (for comctl32:
oleacc, winmm, uxtheme) must be found another way. To be solved in iteration 2,
when writing `check`.

For the Marwin target, step 2 uses the exports of Marwin's builtin modules (§3).

## 7. Live check (`verify`)

`WINEPREFIX=… WINEDEBUG=+loaddll,warn+module wine <exe>`. Stderr goes to
`$WINEPREFIX/dllmgr/logs/<ts>.log`. The report is compact, at most 15 lines. For
each managed dll: where it was loaded from, native or builtin, whether this
matches the expectation, and the sha256 of the physical file. Plus the "No
implementation …" lines without repeats, at most 10. For a 32-bit program in a
win64 prefix, the path `C:\windows\system32\…` in the log physically means
`syswow64`. Check this against the reference logs from I0.
dllmgr waits for the program to exit; `verify.timeout_sec` (0 means until
exit). The parser is tested on reference logs from the user's machine.

## 8. Catalog

The catalog lives in this repository, in the model of the f4 PlugRing catalog
(decision D1, `docs/decisions.md`): one entry is one Markdown file. The YAML
frontmatter is for the client; the prose below it is for people and is rendered
by GitHub. CI compiles the frontmatter into `catalog/index.json`, the file the
client downloads. There is no backend. Entries come through pull requests. The
catalog carries source, not binaries (D4). The full format and the submission
steps are in `catalog/README.md`.

Layout:
```
catalog/fixes/<tracker>-<number>.md           one file per bug (D2), e.g. winehq-59609.md
catalog/variants/<dll>-<provider>-<version>.md   whole-DLL alternatives
catalog/index.json                            compiled index
libs/                                         libraries such as cc580 (plan:
                                              https://github.com/unxed/dllmgr/issues/1)
patches/                                      patches over DLLs that cannot be replaced (§16)
```

DLLs are a field of an entry, not a directory level (D3). The client finds
entries by DLL name or by program name through `index.json`. The index is a
JSON array sorted by `id`; each element is the frontmatter of one file plus its
`path`. `index.json` is checked in (the client downloads it from the main
branch), and CI fails a pull request in which it differs from the compiled
entries. The tool is `cmd/dllmgr-catalog` (`check <dir>`, `build <dir>`);
the code is `internal/catalog` (§12).

The config has `taps = [{name, url}]`, a list of additional catalogs. Adding an
unofficial catalog gives an explicit warning.

**Kind `fix`**: a source patch for one bug, for example `winehq-59609`.
Fields: `id`, `kind`, `title`, `bug`, `dlls` (a list: one bug can need several
modules, such as comctl32 and comctl32_v6), `patch` (https URL), `patch_sha256`,
`license` are required. `programs` (known affected exe names), `wine` (tags the
patch is known to apply to), `recipe`, `binaries`, `evidence`, `authors`,
`ai_assisted`, `funding` are optional. A binary is built by CI from the patch
and is listed with its sha256; it is never the only form.

Automatic selection uses a planned application identity entry under
`catalog/apps/<app-id>.md`, for example `faststone`. It declares the canonical
ID, aliases, executable names and PE product or vendor identity when available.
A fix or bundle may declare applicability as alternative profiles. All fields
within a profile must match. Profiles can constrain the app ID, app version,
PE machine, Wine target/version and, only where relevant, host architecture or
a detectable backend or hardware capability. A single bug ID can carry several
profiles and builds. A bundle is resolved per installation and may select a
different compatible subset for a different app version or machine.

Use exact app versions or documented numeric version intervals. Match a
validated PE version resource or an explicit catalog identity signal, never a
guess from the directory name. An unknown version matches only a profile that
explicitly supports version-independent use. PE machine controls which DLL can
be loaded. A 32-bit FastStone process needs `i386` DLLs on a 64-bit Wine host
too. Host CPU, GPU and translation constraints are optional and belong in the
profile only when they change the fix's applicability. Unknown constrained
fields yield a skip with a reason. A legacy `programs` match remains useful for
discovery, but is insufficient to declare a fix verified for automatic use.

The resolver only auto-applies entries explicitly verified for the observed
profile and allowed by the user's configured sources. Candidate fixes remain
available for explicit manual testing. The concrete DLL must still pass the
existing hash, architecture, Wine and import checks. Compatible patches to one
DLL are composed on one Wine source base and resolved to one binary. When the
catalog cannot prove a compatible composition, report the conflict instead of
installing one patch over the other. A newer release can replace or supersede
an older fix only through explicit catalog metadata and a compatible plan.

**Kind `variant`**: a whole module not tied to one bug: a module from another
Wine release, or a third-party library such as cc580.

```yaml
---
id: comctl32-wine-11.0
kind: variant
dll: comctl32
file: comctl32.dll                      # file name in the slot
provider: wine
version: "11.0"
arch: i386
slot: system                            # or sxs:microsoft.windows.common-controls
license: LGPL-2.1-or-later
source: https://gitlab.winehq.org/wine/wine/-/tree/wine-11.0/dlls/comctl32
summary: comctl32 (v5) from Wine 11.0
sha256: "…"                             # of the extracted file before unmarking; the result is checked against it
fixes: []                               # ids of fixes the variant already contains, e.g. winehq-59609
fetch:
  urls: [https://dl.winehq.org/wine-builds/ubuntu/pool/main/w/wine/wine-stable-i386_11.0.0.0~noble-1_i386.deb]
  sha256: "…"                           # of the archive
  format: deb                           # deb | tar.xz | tar.zst | raw
  member: "*/i386-windows/comctl32.dll" # glob, exactly one match; not needed for raw
---
```

- The catalog does **not re-upload** Wine DLLs. The entry points to the
  official upstream build, and the file is extracted from it. License and trust
  stay with upstream.
- Third-party providers (cc580): `format: raw`, a release asset. `source` and
  an open `license` are required. Without them the catalog CI rejects the
  entry. Microsoft DLLs are not accepted.
- Variant specification: `dll@provider:version[/arch]`. `latest` is the maximum
  version (compared by numeric components). The rule stores the concrete
  version.
- A .deb is parsed this way: ar (own parser, about 50 lines) plus
  `data.tar.{xz,zst}` through `github.com/ulikunitz/xz` and
  `github.com/klauspost/compress/zstd` (pure Go).

Publishing:
- A pull request that adds a file to `catalog/fixes/` or `catalog/variants/`,
  with the rebuilt `index.json`.
- `dllmgr add-local <file.dll> --provider P --version V`: a local variant
  without the catalog (for DLL authors and for fix-it-in-wine).
- `dllmgr pack <file.dll> --provider … --version … --url … --source … --license …`:
  prints the frontmatter of a variant entry with hashes, bitness and the result
  of the import check against the local Wine.
- Later: `pack-wine <archive> --version X`: entries for all replaceable DLLs
  of a Wine release. Catalog CI: format check (exists), hash check, and a matrix
  of import compatibility over several Wine versions.

## 9. Local paths and config

`~/.config/dllmgr/config.toml`; `~/.cache/dllmgr/dl/<sha256>` (archives, may be
deleted); `~/.local/share/dllmgr/store/<sha256>.dll` (the local cache; mark
cleared); `~/.local/share/dllmgr/index/<tap>/` (downloaded catalogs);
`$WINEPREFIX/dllmgr/{state.json,history.jsonl,backup/,logs/}`.

Config: `wine.binary="wine"`, `wine.dll_dirs=[]`, `prefixes=[]`, `taps=[…]`,
`strict_imports=true`, `verify.debug="+loaddll,warn+module"`,
`verify.timeout_sec=0`, `keep_archives=true`.

## 10. CLI

The commands below describe the planned manager. The default interaction is
the one-step **Fix** action, with no DLL, slot or variant choices required.

| Command | Behavior |
| --- | --- |
| `dllmgr fix faststone` | Discover FastStone in the selected prefix and apply its verified, compatible fixes as a set. Follow the app after a successful apply unless `--no-follow` is set. |
| `dllmgr unfix faststone` | Remove the managed FastStone fix set and its subscription. Restore the original DLLs and override values where no other rule still needs them. |
| `dllmgr fix world` | Discover all known apps in the selected prefix and apply each compatible fix set. Print unmatched, ambiguous or incompatible cases and continue with independent apps. Follow only the apps successfully fixed, without retaining a wildcard subscription. |
| `dllmgr unfix world` | Remove app fix sets and their subscriptions in the selected prefix. Leave manually added DLL rules in place. |
| `dllmgr follow faststone` | Subscribe to FastStone in this prefix, even before a compatible fix exists. |
| `dllmgr unfollow faststone` | Stop updating this app automatically through `upgrade`. Keep the current fixes. |
| `dllmgr update` | Refresh configured catalog indexes. Keep the previous index if validation fails. Alias for `index update`. |
| `dllmgr upgrade` | Re-detect followed apps and reconcile their verified fix sets against the refreshed index. This can add new fixes, update old ones, and remove superseded or explicitly inapplicable rules as part of one compatible plan. |

`dllmgr fix` without a name is implemented as the first step of `fix world`
(D18): it scans `drive_c`, matches recipe rows and asks before each apply.
The installer adds a menu entry that runs it, for use without a terminal.

Discovery checks the selected prefix's Windows registry and scans its owned
drive roots recursively, including portable apps outside Program Files. It
also checks external roots the user explicitly adds. It deduplicates paths,
never launches executables to identify them, and does not traverse links or
drive mappings outside the allowed roots. In particular `Z:` is not a default
scan root. If several installations share an executable basename, the planner
checks all of them before setting a basename-wide Wine rule. A user-supplied
path identifies the target installation but does not isolate the Wine override.
If versions or architectures require incompatible effective rules, report the
affected paths and require separate prefixes for those selections.

`dllmgr update && dllmgr upgrade --yes` is the manual unattended-friendly
flow. `--dry-run` prints the plan without writing files or registry values.
`--yes` accepts the computed plan without interactive input. Conflicts,
untrusted sources, missing verification and active target processes still block
the affected changes. The command reports per-app outcomes and returns a
failure status if a planned operation could not complete. A failed refresh
keeps the previous index, and a failed upgrade transaction keeps the previous
selection for the affected apps. Missing metadata alone is insufficient to
remove a managed rule. A distro or external scheduler can invoke these commands
later. Service and scheduling policy belong to that integration.

State 2026-11-11 (#86): there is no separate catalog index yet; the catalog,
the runtime pin and the recipes ship inside dllmgr itself. So `dllmgr update`
installs the latest dllmgr commit from GitHub (verified blob by blob, the
install.sh layout, old commits kept, `--revision` to go back) and reports the
changed pins, and `dllmgr upgrade` reconciles the apps that have a private
fix journal (`<prefix>/.dllmgr/apps/*.json`: FastStone, Photoshop CS2) against
the running dllmgr's pins (runtime package sha256, module release, dllmgr
commit) by re-running their `fix`. Gaps against this section: no
follow/unfollow (every fixed app is followed), no re-detection of moved or
new installations (a missing executable is held back), only the default
prefix plus `--prefix` (no prefix registry), and the prefix-wide fixes
(`faststone-fonts`, `faststone-avif`) and legacy shared FastStone journals are
not reconciled.

Advanced commands remain available for authors and manual overrides.

```
dllmgr index update
dllmgr search <dll>            dllmgr info <variant>
dllmgr check <variant> [--app <exe-path>] [--target wine|marwin]
dllmgr check --target marwin <dll|exe>
dllmgr apply --app <exe|path> <variant> [--slot …] [--prefix …] [--yes]
dllmgr remove --app <exe> <dll>      dllmgr reset      dllmgr undo
dllmgr status                        # rules, mismatches, "Wine changed since apply",
                                     # "the builtin is not older than the variant: the rule can be removed"
dllmgr verify --app <exe-path>
dllmgr add-local …   dllmgr pack …   # pack prints the frontmatter of a catalog entry
dllmgr gui
```
`--target wine|marwin` selects the target (§3). The default is `wine`.
The default prefix is `$WINEPREFIX`, otherwise `~/.wine`. Before any change the
plan is printed; `--yes` skips the confirmation.

## 11. GUI on goWidgets

goWidgets has native controls and no CGO. It has Window, Label, Button,
CheckBox, Edit, ComboBox, ListBox, Table, TextView, ImageView, Canvas,
Message/Confirm/Ask, file dialogs and a tray. It has a headless backend. Before
work, read the README, `docs/disdoc.md`, `docs/adr/` and `AGENTS.md`.
If a needed widget is missing, stop and ask. Do not write widgets inside dllmgr.

The default view is an application list for the selected prefix. The primary
action is **Fix** for a selected app and **Fix all** for the whole prefix.
Show the detected app version and architecture, available fixes, conflicts and
follow status. Offer **Unfix**, **Unfix all**, **Follow**, **Unfollow**,
**Refresh catalog** and **Apply updates** using the CLI policy from §10. Show
the resolved plan and its result in the log. The advanced view exposes the
program/DLL/variant/state table and manual rule editing.

The "Add" scenario:
1. A file dialog selects the exe.
2. The label "Rule for all FSViewer.exe in the prefix ~/.wine".
3. ComboBox of DLLs (filtered by the bitness of the exe).
4. ComboBox of variants: newest first, with the result of `check`.
5. "Apply" -> Confirm with the text of the plan -> reconcile -> offer "Check by
   running".

The GUI is a thin layer over the same packages as the CLI. There is no logic in
the UI.

## 12. Code structure

```
cmd/dllmgr/        CLI + the gui subcommand
cmd/dllmgr-catalog/  `check <dir>` and `build <dir>`: validate the catalog, compile index.json
internal/pe/       PE parser: machine, imports (name/ordinal/delay), exports + forwarders,
                   builtin/placeholder marks, PREFER_NATIVE, Unmark()
internal/wine/     Wine lookup, version, dll directories, unix part, run with WINEDEBUG
internal/prefix/   prefix arch, slot resolution
internal/reg/      Registry interface; implementation through `wine reg add/query/delete`; fake
internal/catalog/  catalog entries: frontmatter parser, validator, index builder
internal/index/    index.json reader, catalogs (taps), variant specification parser, latest
internal/fetch/    download with cache, sha256, deb/tar.xz/tar.zst/raw
internal/store/    local cache by sha256
internal/compat/   import check
internal/state/    state.json, history.jsonl, reconcile()
internal/verify/   parser of +loaddll / warn+module
ui/                goWidgets
catalog/           catalog entries (Markdown + frontmatter) and index.json
libs/              libraries (cc580)
patches/           patches over DLLs that cannot be replaced
```
The code of the Marwin target is added next to `internal/wine/` when the target
starts (§3).
TOML: `github.com/BurntSushi/toml`; YAML (catalog frontmatter): `gopkg.in/yaml.v3`;
everything else is the standard library.

## 13. Tests

- `testdata/`: tiny PE files (DLL/EXE, i386 and x86_64) built with mingw. They
  are stored in the repository together with `testdata/gen.sh`. Copies with the
  builtin mark are created in the tests themselves.
- pe: imports by name, by ordinal and delayed; exports, forwarders; `Unmark` is
  idempotent and changes exactly 32 bytes; a placeholder is rejected.
- compat: A imports `B.f1, B.f2, B.#7`, B exports only `f1` -> the report is
  `f2, #7`.
- state: a fake prefix in `t.TempDir()` (`system.reg` with `#arch=win64`,
  `syswow64/comctl32.dll` with the mark) plus a fake Registry.
  - add -> files and registry; remove -> byte for byte as before.
  - Mismatch -> error without changes.
  - Conflict.
  - The symlink target is not touched.
  - A failure after the first operation -> a repeated reconcile completes it.
- fetch: a .deb is built in memory (ar + tar.xz / tar.zst) -> extraction. A hash
  mismatch, or 0 or 2 glob matches -> error.
- verify: reference logs from I0 (supplied by the user).
- The real Registry is an integration test, only if `wine` is in PATH.
- GUI: a smoke test on the headless backend, if it allows.
- Run builds and tests in the sandbox only with the user's permission; first
  send a patch.

## 14. Iterations

- **I0: manual spike, no code** (script below). Checks H1-H4 and gives reference
  logs. The result decides whether the sxs slot is needed already in I1.
- **I1: minimal CLI:** `add-local`, `apply`, `remove`, `reset`, `undo`, `status`
  for a local file; no catalog and no network. Slot system (+sxs, if I0 requires
  it), unmarking, checks a, b, c, e, f, g. This already covers the user's
  scenario: download the deb by hand -> add-local -> apply.
- **I2:** `check` (imports), `verify` (+loaddll) and `diag` with the presets
  `load` and `crash` (§17).
- **I3:** the catalog and download; `apply --app FSViewer.exe
  comctl32@wine:latest`. The first catalog content is comctl32 and comctl32_v6
  from Wine 11.0.
- **I3a:** application discovery and applicability profiles. Implement `fix`,
  `unfix`, `follow`, `unfollow`, `update` and `upgrade` on top of the same
  planner and reconciler. Exercise FastStone as the first end-to-end app.
- **I4:** GUI with **Fix** and **Fix all** as the primary actions, using the
  same planner and subscriptions as the CLI.
- **I5:** `pack`, `pack-wine`, catalog CI.
- **I6:** patches (§16): the entry DLL, the loader `dmpatch.dll`, `dmpatch.h`,
  the first patch.
- **I7:** `diag`: the presets `relay:<dll>` and per-DLL presets, `--compare`
  (§17).
- **Marwin target:** no fixed number. It starts when Marwin has a PE loader
  (§3).
- Not planned now: placement next to the exe (different variants for different
  programs in one prefix; first check the search order and KnownDLLs in Wine),
  Windows as a target for cc580, catalog signatures, variant sets (v5+v6
  together; decided after I0).

### Spike I0

Script: [`spike/spike0.sh`](../spike/spike0.sh).
Order: `probe` (changes nothing) -> from the paths in the log choose `system` or
`sxs` -> `apply` -> `probe` -> check the bugs by hand -> `undo`. The output of
both `probe` runs is the reference log for I2.

## 15. Open questions and risks

- The name of the manager. The code, the catalog, the libraries and the patches
  are in this repository.
- If comctl32 from Wine 11 needs exports that Wine 9 does not have, this variant
  is marked "incompatible with Wine 9". cc580, written on the public API, has
  the advantage here.
- Links beyond imports (uxtheme, window classes shared by v5 and v6) are caught
  by `verify` and by user reports.
- The distribution updated Wine -> `status` shows that the rule may be outdated.
- Security: a DLL is code. The sha256 hashes are pinned, sources are required,
  third-party catalogs only with explicit consent.
- The Marwin target: open items are listed in §3.
- Delay-import descriptors in Wine's own builds: see §6.

## 16. Patches over DLLs that cannot be replaced

DLLs with a unix part, and the system core (ntdll, user32, gdi32, win32u …),
cannot be replaced. Their PE part is tied to the unix part and to wineserver by
an internal protocol of a specific Wine version. For them there are **patches**:
small DLLs that are loaded into the process of the program and replace the
behavior of single functions. Patches live in the same catalog as variants
(`patches/` and the entries in `catalog/`), under the same rule model (§4) and
with the same rollback. Neither the exe of the program nor Wine is changed.

How a patch gets into the process:
1. **Entry DLL.** A copy of a builtin leaf DLL of the same Wine as the user's
   (for example `version.dll`), with one added import: `dmpatch.dll`. The code
   is not changed, so compatibility is guaranteed. It is installed by a regular
   rule: unmarked, `native,builtin` for this exe. Adding an import to a ready PE
   is a known technique (`setdll` from Microsoft Detours does it): a new section
   with a copy of the import descriptors and one new descriptor, and a rewritten
   pointer to the import directory. We write this in Go in `internal/pe`.
   - Which DLL to take: the first replaceable one among the static imports of
     the exe, by a preference list (`version`, `winmm`, `msimg32` …; the list is
     in the config). If none fits, it is an error asking the user to choose by
     hand.
   - The entry DLL is a derived variant: it is computed from the builtin DLL of
     the target Wine. After a Wine update, reconcile recreates it, and does not
     report a mismatch.
2. **The loader `dmpatch.dll`** (ours, small). In DllMain it takes the exe name
   of the process and loads all DLLs from `C:\windows\dllmgr\patches\<exe>\` in
   name order. The directory layout is the config; no parser is needed. One
   entry DLL per prefix serves different sets of patches for different programs.
3. **Hooking** inside a patch. By default through the IAT of the needed modules
   (the exe and, if needed, other DLLs, for example the calls comctl32 ->
   user32). For modules loaded later: `LdrRegisterDllNotification`. If a call
   must be caught everywhere, an inline hook with a ready library (MinHook,
   BSD-2).
4. For authors: `dmpatch.h`. It has IAT and inline hooks, a notification of
   module loads, and a log in the Wine format (§17). Patches are written in C
   (mingw) or in Bp.

The catalog entry of a patch is a fix entry (D2): `catalog/fixes/<tracker>-<number>.md`,
keyed by the bug it works around, with these extra frontmatter fields (added to
`dllmgr-catalog` when I6 starts):
```yaml
method: patch                       # a patch over a DLL that cannot be replaced
targets: ["user32!GetScrollInfo"]   # what it hooks: for display and for finding conflicts
```
`programs` lists the programs it was made for; its source lives in `patches/`.
`source` and `license` are required. The catalog CI builds patches from sources
itself and does not accept binaries. Two patches on one function of one program
give a warning; the order is by name.

Hypotheses (checked at the start of I6):
- **H5.** Wine loads an entry DLL with an added import as a regular native DLL
  (visible in `verify`).
- **H6.** LoadLibrary from the DllMain of the loader does not hang under Wine
  (common practice of plugin loaders). If it hangs, the fallback is patches
  directly in the imports of the entry DLL. The price is one entry DLL per set
  of patches.
- **H7.** `LdrRegisterDllNotification` exists in Wine 9 (check against
  `dlls/ntdll`).

## 17. Debug-data collection (`dllmgr diag`)

An agent (the fix-it-in-wine skill) or a person must not invent each time how to
get the data. One command collects a bundle of fixed structure with a short
digest.

`dllmgr diag --app <exe-path> [--preset P …] [--compare <variant>] [--timeout N]`

Bundle `$WINEPREFIX/dllmgr/diag/<ts>-<exe>/`:
- `facts.json`:
  - versions of Wine, the distribution and the kernel; the architecture of the
    prefix;
  - active overrides (environment variable, AppDefaults, global);
  - dllmgr rules and their state;
  - the exe: sha256, version from resources, bitness, static imports;
  - loaded modules (from `+loaddll`): native or builtin, file hash.
- `digest.txt`: a digest of at most 60 lines:
  - loaded managed DLLs;
  - "No implementation";
  - exceptions (code, module + offset);
  - the first `err:` lines and the most frequent `fixme:` lines;
  - for relay: the most frequent calls of the target DLL.
- `logs/*.log.zst`: full logs, compressed. The size is limited (ring buffer, the
  limit is in the config).

Presets are data (TOML in `presets/`) and grow the same way as the catalog:
- `load`: `+loaddll,warn+module`. What was loaded and which functions were
  missing.
- `crash`: `+seh,+loaddll` and a backtrace. How to get a backtrace without a
  dialog (winedbg in automatic mode through the AeDebug key) is to be clarified
  in I2.
- `relay:<dll>`: `+relay` for this DLL only. The values `RelayInclude` and
  `RelayExclude` in `HKCU\Software\Wine\Debug`. They are set for the time of the
  run and restored through the same registry layer.
- `<dll>`: the channels of a given DLL. They are generated from the Wine sources
  of the needed tag: `WINE_DEFAULT_DEBUG_CHANNEL` /
  `WINE_DECLARE_DEBUG_CHANNEL` in `dlls/<dll>/*.c` (`dllmgr presets gen`).
- Our DLLs and patches (cc580, §16) write a log in the Wine format
  (`trace:<channel>:<function> …`) and read the same `WINEDEBUG` variable, so
  the same code parses them.

`--compare <variant>`: the same scenario runs twice, as is and with the variant
applied temporarily (a temporary set of rules through reconcile, then a return).
The output is the difference of the digests. fix-it-in-wine uses this for the
bisection of a DLL.

Scenario: interactive (the user works in the program and closes it) or a minimal
repro program supplied by the caller. Scenarios with xdotool come later.

## 18. Related: fix-it-in-wine

The AI agent skill "fix my application under Wine" lives in
https://github.com/unxed/fix-it-in-wine. It uses dllmgr to apply, undo, verify,
collect diagnostics (`diag`) and install patches. What it may send to Wine is
limited by the clean-room rules in D16; the reasons are in
[vision.md](vision.md). Until dllmgr exists, the skill
ships small stand-in tools.

## 19. Exchanging fixes (concept, not planned yet)

A fix that an agent writes on a user's machine (see fix-it-in-wine) reaches Wine only as a text
report; the patch itself stays with that user. The next user of the
same program should not have to repeat the work. dllmgr can carry such fixes between users. How
to host this and how to pay for it is not decided. This section only lists what the architecture
must allow from the start.

Fixes are keyed by bug: the unit of exchange is the file `catalog/fixes/<tracker>-<number>.md`,
for example `winehq-59609` (decision D2 in [decisions.md](decisions.md)). The program is a field
of the entry, not its key. The catalog already carries this shape; the hooks below are what is
still missing.

What is exchanged — a **fix package**:
- base: a Wine tag or commit, or a library from `libs/`;
- the change as source (a patch), never only a binary;
- the build recipe, so anyone can rebuild it and compare the hash with the published binary;
- what it is for: program (exe name, version, sha256), DLL, symptom, WineHQ bug number;
- the evidence: digests before and after, the reproducer described in words;
- license and authorship, including whether it is AI-assisted (`ai_assisted = true`): some
  maintainers ask for that note, for example in Baron-von-Riedesel/HX#76.

Licensing limits:
- A changed Wine DLL is LGPL; whoever distributes it must give the source under the LGPL. A
  closed, paid binary of a changed Wine DLL is not possible. Selling can only be about the work
  (bounties, early access, support), not about exclusive rights.
- Own libraries (such as cc580) may have their own license, which the entry states.

Hooks to keep in the design now:
1. **Federated catalogs.** Any person or group can publish a catalog (a git repository with
   entries) and dllmgr can add it, with an explicit trust warning. Our servers are not needed;
   hosting costs fall on whoever publishes.
2. **Content-addressed artifacts.** An entry names files by sha256, so any mirror can serve them.
3. **Reproducible builds.** A package without a recipe that reproduces its binary is not trusted
   by default; a catalog's CI can rebuild packages itself.
4. **Publisher identity.** An optional signature field in the entry (a publisher key), checked
   when present.
5. **Reports from users.** An optional "works / does not work" record per program version and
   Wine version, sent only with the user's consent, aggregated by the catalog.
6. **Money stays outside dllmgr.** An entry may carry a `funding` URL (a bounty or donation
   page on an existing platform). dllmgr only shows the link; it never handles payments.
7. **Requests.** fix-it-in-wine, when it cannot fix a problem, can draft a request ("this
   program, this symptom, this digest") for a catalog, posted only with the user's approval —
   the start point for a bounty.
8. **Vendor kits.** A software vendor can ship a recipe's modules inside its own package,
   active only under the Wine releases they were measured on. See
   [vendor-kits.md](vendor-kits.md) (D19).

## Planned default terminal administration

Owner decision D22: add a TUI using [vtui](https://github.com/unxed/vtui), with
checkboxes for selecting fixes and buttons for applying, removing and undoing
selections. Bare `dllmgr` should open it by default once it exists. Retain the
explicit CLI commands for automation and share the install/undo engine between
interfaces. This is a recorded plan; implementation is deferred.
