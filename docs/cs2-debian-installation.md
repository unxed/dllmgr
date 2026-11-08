# Photoshop CS2 trial installation on the Debian cloud stand

Installation authorized by the owner on 2026-11-08. Record observations and
messages; new problems are deferred **after existing bugs**, including #31,
#35 and #36. This installation does not start the broader Wine bug audit.
The separate Ubuntu/Claude stand has its own [findings](sandbox-findings.md);
do not merge results from different environments or duplicate those issues.

## Exact environment and source

- The reproducible [Debian Wine stand](cloud-wine-sandbox.md): WineHQ
  11.0.0.0~trixie-1, full-system QEMU TCG, Debian 6.12.115+deb13.1-amd64,
  Openbox, Xvfb :191 3072x1728x24, Windows DPI 192.
- New, independent **win32** prefix:
  `/workspace/work/photoshop-cs2/prefix110`. No owner files or existing trial
  prefix copied. Optional Mono/Gecko are disabled by the stand's documented
  `WINEDLLOVERRIDES=mscoree,mshtml=`; the VM has no external NIC.
- Official Adobe HTTPS installer, source/size/SHA256 in
  `experiments/cs2-debian-installation/installer-source.json`.
  345068035 bytes, SHA256
  `919b642d910995089a21c27780eb4e54140ac917549d7d34ceab6157c01d02ea`.
  Native `unzip -t` reports no compressed-data errors (488 entries,
  379594548 bytes unpacked). This is a container integrity check, not proof
  of successful installation or Photoshop execution.
- Raw observations, screenshots, action journal and prefix are under
  `/workspace/work/photoshop-cs2/`. Never commit Adobe binaries, prefix contents,
  license values, user documents or unreviewed installer logs.

## Observed stages

1. New prefix initialized successfully. Windows DPI 192 set before Adobe launch.
2. Official self-extractor launched. UI title: `WinZip Self-Extractor -
   Photoshop_CS2.exe`; default extraction folder identifies `Photoshop TryOut`.
The reviewed prefix-initialization log is retained in
`experiments/cs2-debian-installation/wineboot.txt` (test path normalized).

3. Extraction target explicitly set to `C:\AdobeCS2-Extract` and Unzip clicked.
   Completed: WinZip reported `404 file(s) unzipped successfully`; all 404
   extracted files matched archive sizes and CRCs. Still separate from MSI
   installation and app launch.
4. First absolute-path launch from an unrelated working directory showed
   `Error: .\AutoPlay\main.ini`, then `MAIN_FILE_VERSION`. The first process
   remained alive; a simultaneous retry returned 1. The stale failed instance
   was terminated, and a new launch after `chdir` to the installer directory
   reached the normal Adobe language picker. This establishes the working-
   directory workaround, not an upstream Wine bug or a Photoshop fix.
5. Current checkpoint: language picker. **No successful MSI installation or
   Photoshop launch has yet been claimed.**

## Deferred observations

These are observations, **not established upstream Wine defects**. Preserve
exact messages, applicability and evidence before selecting fixes. No change
to Wine/Photoshop has been made to suppress them.

| ID | Stage | Exact message / observation | Interpretation and priority |
|---|---|---|---|
| D1 | Fresh wineboot, before Adobe | `err:vulkan:vulkan_init_once Failed to load libvulkan.so.1` | Local runtime lacks this optional graphics library; no Photoshop failure attributed. Deferred environment integration. |
| D2 | Fresh wineboot, before Adobe | `StdMarshalImpl_MarshalInterface Failed to create ifstub, hr 0x80004002`; `CoMarshalInterface ... hr 0x80004002`; `apartment_get_local_server_stream Failed: 0x80004002`; `start_rpcss Failed to open RpcSs service` | Same class as existing Ubuntu finding F6, now separately observed on Debian. Prefix initialization still returned 0. Do not duplicate or declare a root cause. |
| D3 | Fresh wineboot, before Adobe | `winebth` start/control errors 1359/1062; `do_file_copyW Unsupported style(s) 0x10`; `winebus` and `wineusb` driver load `c0000135`, service errors 126/1062; `Failed to initialize Unix library, status 0xc0000135` | Bluetooth messages/style warning overlap F6. USB/bus support is not validated in this extracted-runtime VM; deferred stand integration, not an installer failure. |
| D4 | Fresh wineboot, before Adobe | `err:winediag:getaddrinfo Failed to resolve your host name IP` | Guest networking/hostname limitation; no external NIC. Deferred; do not impute to Photoshop. |
| D6 | Root Setup.exe / autorun | `Error: .\AutoPlay\main.ini`, then `MAIN_FILE_VERSION` | Launched from wrong cwd; file exists and CRC matches. Retry after stopping failed singleton and setting cwd reaches language picker. Preserve this launch requirement; defer any broader launcher investigation. |
| D5 | Self-extractor first screenshot | First frame was black while the X window was already present; the next stable screenshot painted the WinZip UI | Readiness/timing observation under CPU emulation. A transient screenshot is not proof of a persistent paint defect. |

Wineboot and extraction are distinct from MSI installation and from the
installed application's first trial launch. Track their outcomes separately.

## Continuation checkpoint and local evidence

`experiments/cs2-debian-installation/checkpoint.json` states the exact last
verified stage. `actions.jsonl` is the reviewed chronological record (repetitive
X frame trees omitted); screen hashes are in `screenshots.json`. Screenshots
remain local, and no Adobe program, installer, prefix or license is committed.
Newly found observations remain below existing bug priorities.

The saved controller/client/sequence scripts run through the prepared VM, with
explicit JSON requests and file-backed process logs. They use the dedicated
CS2 prefix, not the smoke prefix. `windows-install.c` is the existing public
Win32 enumeration helper plus a WM_SETTEXT operation; HWNDs/PIDs in the log
are historical and must be re-enumerated. A successful WM_SETTEXT return is
what matters; an uncleared GetLastError value on success is not a failure.

Local MinGW package versions and SHA256 are in `toolchain.json`. Compile with
`i686-w64-mingw32-gcc-posix -O2 -s windows-install.c -o windows-install.exe
-luser32` using the extracted toolchain's usr/bin in PATH. Do not commit the
executable. Restore the script files to the paths in checkpoint.json, create
control/{requests,responses} and evidence/, then run:

```sh
python3 /workspace/work/wine-stand/run.py --timeout 7200 -- \
  /usr/bin/python3 /workspace/work/photoshop-cs2/control/controller.py
```

Controller readiness is control/ready.json. The client waits for a complete
JSON response; a transient empty file on the uncached 9p share must not trigger
a retry of an already executed button click. Source/archive contents should be
restored from the exact official download and hash, not committed binaries.
