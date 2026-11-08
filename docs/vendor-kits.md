# Vendor kits

Status: proposal for the owner's review, 2026-11-06 (D19).

A vendor kit lets a software vendor ship our fixed DLLs inside its own
package. Under Wine the program then works out of the box, with no dllmgr and
no action from the user. Example: FastStone's developers add the kit for
FastStone 8.5 to their installer and their portable archive.

"Kit" is used instead of "bundle" because `catalog/bundles/` already holds
recipes.

## What a kit is

A folder the vendor copies into its package, made by a planned command
`dllmgr kit <recipe> --out DIR`:

```
wine-fixes/
  README.txt            what this is, how to turn it off, links
  wine-11.0/i386/comctl32.dll       one folder per `when` row: Wine tag and
  wine-11.0/i386/comctl32_v6.dll    PE architecture; modules already unmarked
  wine-11.0/i386/gdiplus.dll
  SHA256SUMS
  COPYING.LIB           the LGPL 2.1 text
  SOURCE.txt            where the corresponding source is
  recipe.txt            the recipe page at the commit the kit was made from
```

A kit is a view of one recipe at one commit: the same fixes, the same `when`
rows and the same `release` assets. It adds no file kind and no key to the
catalog (D14).

## Only under Wine

The kit is active only under Wine. Wine-built modules call Wine-specific
functions and are tested only against Wine. On Windows the Microsoft module is
the reference, and a Wine module next to the exe could replace it. So the kit
never places a module where Windows would load it.

"Always on" makes sense only for a module designed to run on Windows too, such
as cc580 (issue 1). That would be a later kind of kit.

Detecting Wine: Wine's ntdll exports `wine_get_version` (and
`wine_get_build_id`). Wine's
[Developer FAQ](https://gitlab.winehq.org/wine/wine/-/wikis/Developer-FAQ)
calls detecting Wine a bad idea for changing program behavior, and documents
this export as the way to do it. The kit uses it only to choose modules that
were measured on that exact Wine release. If the release has no folder in the
kit, the kit does nothing and Wine's own modules stay in use.

## How the module gets loaded

Facts from `concept.md` (F1–F3), checked in `dlls/ntdll/unix/loadorder.c` of
`wine-11.0`:

- Without a DLL override Wine loads its builtin module, even when a file with
  the same name lies next to the exe. Copying the file is not enough.
- An override value can name the module by its full path without extension,
  or apply per exe under `HKCU\Software\Wine\AppDefaults\<exe>\DllOverrides`.
  The value is `native,builtin`.
- The file must not carry the "Wine builtin DLL" mark (F1). Kit modules are
  unmarked when the kit is made.

Two ways to activate, to be chosen by experiment:

- **A. At install.** The vendor's installer, under Wine only, copies the
  modules for the current Wine release into the program directory and writes
  the per-exe override. The uninstaller removes both. Simple, but a later Wine
  upgrade leaves modules from the old release in use. Wine's own upgrade does
  not overwrite them (F4).
- **B. At each start.** A small launcher (a plain Win32 program shipped in the
  kit) checks the Wine release on every start, installs or removes the
  modules and the override to match, then starts the program. It follows Wine
  upgrades. The vendor must start the program through it.

Open: how comctl32 v6, which comes through the side-by-side manifest, is best
placed per application. The old system/SxS-slot method was unsafe and is
disabled: a per-exe override does not isolate a shared file. The current
FastStone method uses a private runtime with exact image-path selection;
see [scope and launch requirements](app-isolation.md).

## License

This is not legal advice; the vendor decides with its own lawyer. Wine is
LGPL-2.1-or-later, and so are the fixed modules. As we read the license:

- The modified modules stay under the LGPL, and the changed files carry
  notices of the change (section 2). Our patches and fix files are that
  notice.
- Whoever distributes the modules must give the complete corresponding
  source, or equivalent access to it from the same place (section 4). Patches
  against a public Wine tag are a review aid; to be safe, dllmgr CI publishes
  a source archive (the Wine tag with the patches applied and the build
  commands) next to every release, and `SOURCE.txt` points to it.
- If the vendor's program and the modules are distributed together as one
  work, section 6 may apply: the terms must allow changing the work for the
  customer's own use and reverse engineering to debug such changes. The
  vendor should check its EULA. The user can always replace or remove the
  modules: they are plain files and one registry value.

## How it fits the catalog

- **Trust.** A kit contains only recipes whose fixes have `results` for each
  of the kit's `when` rows (data-model, "Trust").
- **New builds of the program.** A new exe has a new `exe_sha256`, so it
  needs its own `when` row. The vendor runs the recipe's checks against the
  new build in its CI and adds the rows by pull request, or keeps its own
  catalog (concept §19, federated catalogs).
- **Fixed upstream.** When a Wine release fixes the bug, its evidence row
  reads `without: pass`. The next kit leaves that module out for that
  release. Older kits keep working, because they only match exact releases.
- **Other targets.** A ReactOS kit would be another `target` in the same rows
  (issue 13), with a different activation (no per-exe overrides there).

## Plan

1. `dllmgr kit <recipe> --out DIR`: read the recipe, download the `release`
   assets of each `when` row, check `SHA256SUMS`, write the layout above.
2. CI: publish the source archive next to each release.
3. The launcher (B) or the installer steps (A), after the experiment.
4. Pilot with FastStone, with the owner's approval, after its recipe passes
   the gate in [faststone.md](faststone.md#gate-for-wine-bugzilla-reports-and-follow-ups).
