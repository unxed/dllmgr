# Install and share application recipes

A recipe page is a catalog bundle, for example
[FastStone Image Viewer](../catalog/bundles/faststone-all.md). `dllmgr share`
prints the page at the same commit as the install command, so the link shows
exactly what the command applies. Share both so someone can review the fixes
and their scope before running anything.

## Install dllmgr for the current user

On Linux with Git, Bash, tar, flock and Python 3.9 or newer installed, run the installer
from a reviewed checkout of this repository.

```sh
git clone https://github.com/unxed/dllmgr.git
cd dllmgr
./install.sh
```

The installer copies the committed runtime into
`~/.local/lib/dllmgr/<commit>` and links `~/.local/bin/dllmgr` to it. It needs no
sudo and works with an existing dllmgr installation created by this installer.
You can call `"$HOME/.local/bin/dllmgr"` directly when `~/.local/bin` is outside
your `PATH`.

The installer also adds a menu entry, **Fix Windows programs**. It opens a
terminal and runs `dllmgr fix` for the default prefix (see below). To remove
it, delete `~/.local/share/applications/dllmgr-fix.desktop`.

## Fix the programs in a prefix

```sh
dllmgr fix
```

Without an application name, `dllmgr fix` looks through the prefix's
`drive_c` for programs that have a recipe. It hashes each copy and compares
it, the Wine release and the architectures with the recipe's verified rows.
It never starts the programs. For each recipe that matches, it asks before
applying it. When nothing matches, it says which key differs, for example
the Wine release.

- `--dry-run` only prints what was found.
- `--yes` applies without asking, for scripts.
- `--exe PATH` also checks a portable copy. When `WINEPREFIX` is unset and the
  path is inside a prefix's `drive_c`, that prefix is used.

## Generate a link and an install command

```sh
dllmgr share faststone
dllmgr share --url faststone
dllmgr share --command faststone
```

Use an application or installable bundle ID. The default output is the recipe
page URL on the first line and the shell command on the second. The command
fetches the exact dllmgr commit that generated it from the official GitHub
repository, installs dllmgr for the current user, then runs
`dllmgr fix faststone`. Generate it from an installed or checked-out commit
that has already been published to `unxed/dllmgr`. As with any command that
installs software, review it and the referenced commit before running it.

The command inherits `WINEPREFIX` and defaults to `~/.wine` when the variable
is unset. To use a different prefix, export `WINEPREFIX` in the same shell
before running the generated command. For an already installed dllmgr, the
same recipe can be applied or removed directly.

```sh
dllmgr fix faststone
dllmgr unfix faststone
```

`dllmgr unfix FIX` removes one fix (`uninstall` still works as an alias).
To remove every trace of dllmgr, run `dllmgr cleanup`: it undoes every recipe
in every Wine prefix it finds (the default prefix, prefixes under your home
directory that hold dllmgr state, and the prefixes named by dllmgr's menu
entries; add more with `--prefix`), then deletes dllmgr's state in those
prefixes, its runtime and helper caches, its menu entries and dllmgr itself.
`dllmgr cleanup photoshop-cs2` does the same for one fix only. Both ask
before changing anything; `--dry-run` only lists what would be removed.


For FastStone, close all programs in the target prefix before applying or
removing the fix and let its Wine server exit before relaunching the app.
Set `WINEPREFIX` to the prefix you already use for FastStone. If the portable
app lives outside that prefix, pass `--exe /path/to/FSViewer.exe` to
`dllmgr fix faststone`. The fixer uses `curl` and `sha256sum` to fetch and
check the [prebuilt DLLs](https://github.com/unxed/dllmgr/releases) of the release named in the recipe profile.
If the release has not been published yet, `dllmgr fix faststone --build`
builds the same patches from source with Git, GCC, make, flex, bison, and
the i686 and x86-64 MinGW GCC toolchains installed.
