# Application-private DLL fixes

Issue [#25](https://github.com/unxed/dllmgr/issues/25) corrects a design error:
AppDefaults is a basename-based DLL **load-order** rule, not file isolation.
Replacing a file in system32, syswow64 or winsxs can change another program's
behavior. A registry conflict scan does not make a shared replacement safe.
The old product apply path is disabled. Legacy undo remains available.

## FastStone 8.5 / Wine 11.0

The replacement uses an explicit private Wine runtime. It keeps the original
EXE, installed system Wine and shared prefix DLLs intact. The private loader
selects DLLs only for the complete Windows executable path, rechecking the
image in each child process. A different executable in the same directory,
another copy with the same basename elsewhere, and unrelated children keep
ordinary Wine loading. Explicit system-DLL paths also keep ordinary behavior.

The runtime package fingerprints the exact supported WineHQ 11.0 base. The
installer rejects another build rather than mixing incompatible core modules.
A private copy of Unix modules and launcher files avoids writes through links
into system Wine. Unchanged PE/data files are links; a base upgrade is detected
before launching. The private runtime uses Wine 11's new WoW64 mode for this
verified win64-prefix profile. This does not change the system Wine launcher. The prefix must already match
the stock Wine core DLLs and wine.inf update timestamp; private launch refuses
a prefix needing initialization or a Wine upgrade.

```sh
dllmgr fix faststone
dllmgr run faststone -- /path/to/picture.jpg
dllmgr status faststone
dllmgr uninstall faststone
```

Use `--exe /full/path/to/FSViewer.exe` when several installations exist, and
`--prefix /full/path/to/prefix` to select a prefix. Fixes remain tied to the
selected full path and executable SHA256. Files are stored under
`C:\dllmgr\apps\faststone-<path-id>\<content-hash>`; ownership is recorded in
`.dllmgr/apps/faststone-<path-id>.json`. Install/update/undo use the prefix lock,
verify owned hashes and preserve unrelated files. Pending launcher transactions
roll back at the next command. A changed executable, DLL, runtime or launcher
requires inspection; it is never silently overwritten.

The installer creates a dedicated application-menu entry. To route an existing
FastStone desktop/MIME entry through the private launcher, pass
`--desktop-entry /full/path/to/entry.desktop` (repeatable). Previous entry bytes
are saved for undo. Direct `wine FSViewer.exe` and external Windows shortcuts
bypass this runtime and therefore do not enable these private DLL fixes. There
is no global wine wrapper. Close an already-running FastStone before relaunch:
its single-instance handling may otherwise forward files to the old process.

A runtime package may additionally replace whitelisted Unix module groups
(`scripts/private_runtime.py` `OPTIONAL_GROUPS`), all-or-none per group, with
base fingerprints for the replaced originals. First group: `win32u.so` +
`winex11.so` for `patches/winehq-60721.patch` (issue 27: they share
`struct window_surface`). The packaged release does not ship it yet.

The `--runtime-package FILE` option is for an explicitly trusted offline ZIP.
Normal installation downloads a SHA256-pinned release. Its complete modified
Wine source, patch, build scripts and LGPL notices accompany that release.

## Existing legacy installations

First retain the old journal and backups. Use the matching old undo command
only when the current DLL and original backup match their journal hashes.
The new installer refuses a remaining legacy FastStone entry. A malformed
journal, unknown replacement or missing backup needs recovery from a separately
verified original; do not invent hashes, use `--force`, or delete the journal
to persuade an installer that a prefix is clean. The laptop incident had such
an inconsistent journal, was archived privately and was recovered against the
exact installed Wine 11.0 modules.

`DLLMGR_UNSAFE_SHARED_RESEARCH=1` retains the historical apply engine for
explicitly disposable CI/reproducer prefixes. It is not a product installation
option. It is never set by the product launcher.

## Separate prefix-wide assets

The Tahoma Bold workaround changes the prefix's font selection. The AVIF WIC
registration is visible to all 32-bit WIC applications in that prefix. Those
explicit commands remain separate and are **not** included in the app-private
DLL operation. Their journals and uninstall commands are preserved. Future
composition must expose these scopes and opt-ins; see [#23](https://github.com/unxed/dllmgr/issues/23).

## Proof levels

The loader CI checks 32/64-bit static imports and runtime loads, Unicode full
paths, same-directory and same-basename counterexamples, inherited child
processes, hostile builtin overrides, actual mapped-image markers, explicit
system loads, missing/noncanonical selected paths, and unchanged shared DLL
hashes. Synthetic manager tests cover archive validation, base/runtime integrity,
private ownership, launcher arguments and undo. These are separate from the
real laptop check: FastStone loads private common controls/GDI+, draws a colored
pencil stroke, and the Photoshop CS2 **self-extractor initial window** still
opens and responds while FastStone runs. No further Photoshop installation is
part of this work.
