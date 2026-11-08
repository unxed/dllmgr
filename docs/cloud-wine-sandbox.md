# Rebuilding the cloud Wine test stand

This is environment preparation for [#31](https://github.com/unxed/dllmgr/issues/31),
not a Photoshop retest. The separate [Ubuntu/Claude stand](sandbox-stand.md)
uses root and native i386; its setup is not applicable to this unprivileged
Debian host. Both recipes are retained for their respective environments.
Do not start the research merely because the stand exists.
The owner requested this reusable setup on 2026-11-08. Existing Photoshop results
and next steps remain in [photoshop-handoff.md](photoshop-handoff.md).

## Restore in a new dialog

Use a managed **Debian 13 x86_64** environment with Python 3.11+, curl,
dpkg-deb, `/usr/bin/python3`, `/usr/bin/setpriv`, X11 client utilities
(`xdpyinfo`) and ImageMagick (`import`). These are present in the tested base
image. About 4 GB of writable space and 1 GB guest RAM are needed; allow more
space for applications, prefixes and source builds. No sudo, KVM, system
installation, host i386 support or Docker is required.

From a checkout of dllmgr:

```sh
python3 tools/wine-sandbox/prepare.py \
  --state /workspace/work/wine-stand --workspace /workspace
python3 /workspace/work/wine-stand/run.py --smoke --arch win32
```

Preparation downloads 83 packages into `debs/`, verifies **every SHA256** against
`tools/wine-sandbox/packages.lock.json`, and extracts them locally. The exact
WineHQ URLs and dated official Debian snapshot URLs are in that lock; no package
resolver or moving `latest` URL is needed on restore. Downloads are cached and
verified again on rerun. Preparation also copies the runner into the state
directory. It neither installs packages nor changes the host package database.

The smoke test creates its own `prefix-win32`, initializes Wine, checks `cmd`,
sets and queries Windows DPI 192, opens the i386 PE32 Notepad, types synthetic
text through X11, saves it, verifies the resulting file contents, and captures
the screen. Inspect **`artifacts/result.json`** (`ok: true`), not QEMU's process
exit code alone. `artifacts/processes.log` and `artifacts/serial.log` retain
failures; `artifacts/smoke.png` is the stable synthetic screenshot. The harness invokes `wineboot --init`, not a forced update on every run. First boot
and prefix creation are slow under CPU emulation; the default guest-command
limit is 600 seconds. The host runner allows another 300 seconds for boot and
shutdown. Reuse a clean test prefix for subsequent probes, or remove only this
stand's synthetic prefix to verify fresh initialization.

For a prepared experiment script, after the owner authorizes that experiment:

```sh
python3 /workspace/work/wine-stand/run.py --timeout 1800 -- \
  /bin/bash /workspace/work/my-experiment.sh
```

The command receives private `WINEPREFIX`, `DISPLAY`, `PATH`, `WINESERVER`,
local library paths and XDG directories. The harness sets
`WINEDLLOVERRIDES=mscoree,mshtml=` to suppress optional Mono/Gecko loading and
installer prompts; neither optional component is installed or tested. Account
for that setting before interpreting an application observation. `wine`,
`xdotool` and the X11 client
utilities are available through PATH. The guest starts **Xvfb :191,
3072x1728x24 at 192 DPI**, and **Openbox**, with X TCP disabled. Use scripts
inside the guest to drive windows, collect API traces and save screenshots
under the writable workspace. The guest display is separate from all host
X servers, including a host :191. A per-state lock also blocks preparation while a job is active and prevents two concurrent jobs
from sharing a prefix, task file or artifacts; use separate prepared states
for concurrency. `--arch win64` selects a separate `prefix-win64`; it does not
constitute a verified Photoshop scenario.

Run preparation again to update the copied runner after a repository change.
Keep task scripts in the workspace. The stand path must be a child of the
workspace root; the guest mounts that workspace at the same absolute path.
Do not move a prepared state: Wine's private i386 ELF loader contains its
absolute local interpreter path. Rebuild at the new path instead.

## What runs where

- **WineHQ stable 11.0.0.0~trixie-1**, reported `wine-11.0`, official amd64,
  i386 and common packages. Windows binaries/DLLs are unmodified.
- A full **QEMU system VM**, TCG CPU emulation (`qemu64`, one CPU, 1024 MB),
  **Debian kernel 6.12.115+deb13.1-amd64**, with native i386 execution inside
  that guest. No KVM or guest network device. This is not QEMU user-mode.
- A small generated initramfs contains official static BusyBox and the kernel's
  `netfs`, `9pnet`, `9pnet_virtio`, `9p` modules. virtio PCI support is built in.
- The VM reads the host root through **read-only 9p**, mounts the selected
  workspace separately as writable 9p, and overlays the extracted `root/` as
  another read-only 9p mount. Read-only mounts use `cache=loose`; the mutable
  workspace retains coherent uncached access. The guest loopback is brought
  up even though there is no external network device. It uses guest-local
  tmpfs for `/tmp` and `/run`, plus guest `/dev`, `/proc`, `/sys`. Its Wine job runs with the
  preparing user's UID/GID, not guest root. The mounted root supplies the base
  image's ordinary tools/libraries; this setup is not a portable standalone
  VM disk image and is not intended to run untrusted software.
- The only Wine ELF alteration is `patchelf --set-interpreter` on the private
  `i386-unix/wine` loader, pointing at the extracted Debian i386 ld-linux.
  `wine.original` retains the package bytes. This relocates a dependency;
  it is not a Wine behavior fix. System Wine and shared system DLLs are untouched.

The runner stops its own Wine prefix and process groups in the guest, then
powers the VM off. Ctrl+C stops only the runner's QEMU process group. It leaves
packages, scripts, logs and prefixes for continuation. `vm.pid`/`qmp.sock` are
runtime hints, not persistent identity; never blindly kill a PID saved by an
old session. Remove only your owned state directory to undo preparation.

## Failed approaches: do not repeat blindly

These observations were made in the managed cloud session on 2026-11-08:

1. The host has no sudo or `cloud-agent-packages` helper. `apt-get update`
   against system directories fails with permission errors even through the
   execution tool's escalation. Local package extraction works.
2. Native **64-bit Wine + Xvfb + Openbox works** on the host. Wine cmd,
   Notepad, xdotool input and a screenshot were checked.
3. Native Linux **i386 ELF execution is rejected with `Exec format error`**,
   including the official i386 ld-linux itself. Installing more i386 libraries
   cannot by itself fix that host execution limit.
4. New WoW64 on the host did not give a usable baseline: initialization left
   syswow64/cmd.exe missing, and directly launching Wine's i386 cmd PE terminated
   with SIGSEGV. Adding WINEDLLPATH did not fix that probe. The cause was not
   established, so do not label it an upstream Wine defect.
5. QEMU i386 **user-mode** got as far as `wine --version`. Without
   WINELOADERNOEXEC it failed to exec the loader; with it Wine hit
   `anon_mmap_fixed`'s alignment assertion. QEMU x86_64 user-mode's PE32 command
   probe timed out. Neither approach is the working stand.
6. An early test harness used `subprocess.run(capture_output=True)` for Wine.
   Descendants can inherit those pipes, making the harness wait after the main
   command exits. The reusable harness uses file-backed output and explicit
   process-group cleanup. Interrupted first prefix initialization also left a
   partial prefix unable to load kernel32; recreate that owned synthetic prefix.
7. Use `smm=off`, one `qemu64` CPU and explicit serial boot parameters as in the
   runner; these are the boot settings used for the working VM. No claim is
   made that every other CPU/SMP setting fails.

The temporary probes lived under `/workspace/work/wine-sandbox`; the reusable
stand lives under `/workspace/work/wine-stand`. Old logs or PIDs from those
probes must not override a new run's result.

## Scope and comparison limits

This is a CPU-emulated Debian/Openbox cloud stand. It differs from the owner's
Mint 22.3, stock Wine 11.0, Metacity/Muffin and physical desktop. It can support
API probes and compatibility investigation; timing, GPU, compositor, focus,
hardware and desktop-sensitive results require the relevant real environment.
No real Windows reference machine is provisioned here.

## Recorded verification

`tools/wine-sandbox/verification.json` records the completed checks. The rebuilt
runtime passed the full PE32 cmd / DPI / Notepad / keyboard / save / screenshot
check on an already initialized prefix in 120.9 seconds. The initial window
can be visible with the title `Untitled - Notepad` before the requested document
is loaded; the runner now waits for the document title, sets focus explicitly
and verifies the saved contents. Window visibility or xdotool's exit code alone
is insufficient. Failure screenshots and a live guest process list are retained.
A separate clean-prefix run verifies first initialization; do not confuse a
successful warm run with that result.

Photoshop CS2 has **not** been downloaded, installed or tested during this setup.
The owner's local research files and licensed trial prefix are not present in
the cloud. Preserve trial limits and the existing publication rules. No
WineHQ/GitHub issue comments are authorized merely by preparing this stand.
