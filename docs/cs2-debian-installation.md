# Photoshop CS2 trial installation on the Debian cloud stand

Installation authorized by the owner on 2026-11-08. Record observations and
messages; new problems are deferred **after existing bugs**, including #31,
#35 and #36. This installation does not start the broader Wine bug audit.
The separate Ubuntu/Claude stand has its own [findings](sandbox-findings.md);
do not merge results from different environments or duplicate those issues.

**Latest verified installer result:** product state5, version9.0; exact EXE
hash matches. Installer had F13/F14. First application startup is in progress;
full workspace not yet verified. See checkpoint.json for the last timestamp.

## Exact environment and source

- The reproducible [Debian Wine stand](cloud-wine-sandbox.md): WineHQ
  11.0.0.0~trixie-1, full-system QEMU TCG, Debian 6.12.115+deb13.1-amd64,
  Openbox, Xvfb :191 3072x1728x24, Windows DPI 192.
- Windows version reported by `cmd /c ver`: **10.0.19045**, unchanged.
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
5. North American English selected. The autorun EULA HTML pane was blank;
   the exact official local en_US/License.html was read offline, including
   tryout/evaluation and timeout terms. Normal Accept was clicked.
6. Install Photoshop CS2 launched the standard MSI with SETUPEXEDIR. It
   spent several minutes preparing its GUI in TCG, then showed the normal
   InstallShield Welcome/Next page. Customer Information offered `Install 30-day trial version`; that option was
   explicitly selected, serial stayed disabled/blank, synthetic test identity
   entered. Default destination and file associations were retained. Install
   pressed at 18:05 UTC; MSI now shows Installing Adobe Photoshop CS2.
   **Installation success and first application launch are still pending.**

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
| D7 | Autorun EULA | HTML pane blank, while local official License.html exists and is readable | Stand explicitly disables mshtml/Gecko; configuration limitation, not proven Wine bug. Read verified local terms, then used normal Accept. Deferred. |
| D8 | Autorun | `err:mmdevapi:load_driver Unable to load UNIX functions: c0000135`; ALSA `cannot find card '0'`, `Unknown PCM default` | No virtual audio device, overlaps Ubuntu finding F7. Deferred; autorun continued. |
| D9 | MSI first GUI | Several minutes between MSI process creation and first Welcome page | Processes remained active; Welcome eventually appeared. TCG timing observation, not a demonstrated hang or new upstream defect. |
| D10 | Non-invasive DPI-aware Win32 probe | `SetProcessDPIAware=1 LOGPIXELS=192,192 GetDpiForSystem=192 screen=6144x3456` while Xvfb root is 3072x1728 | DPI 192 is independently confirmed, but Windows/X screen metrics differ. Preserve exact values; virtualization/scaling cause unproven, defer. |
| D11 | Shared-component installation | `err:kerberos:kerberos_LsaApInitializePackage no Kerberos support, expect problems` | Optional authentication integration in the extracted runtime; no Photoshop failure attributed. Deferred. |
| D5 | Self-extractor first screenshot | First frame was black while the X window was already present; the next stable screenshot painted the WinZip UI | Readiness/timing observation under CPU emulation. A transient screenshot is not proof of a persistent paint defect. |

Wineboot and extraction are distinct from MSI installation and from the
installed application's first trial launch. Track their outcomes separately.

## Continuation checkpoint and local evidence

`experiments/cs2-debian-installation/checkpoint.json` states the exact last
verified stage. `actions.jsonl` is the reviewed chronological record (repetitive
X frame trees omitted); screen hashes are in `screenshots.json`. Reviewed screenshots of the synthetic test environment are saved under
`screenshots/`; their blob paths/hashes are in the manifest. Other raw captures
remain local. No Adobe program, installer, prefix or license value is committed.
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

MSI initialization progress was checked with guest process/IO counters, without
debugging or reverse engineering Adobe code. A separate harness JSON-file race
was observed (client saw an empty just-created response); retrying incomplete
JSON fixed the client. It must not trigger duplicate installation clicks or be
reported as a Photoshop/Wine defect.

## Repository update incorporated during installation

At the owner's request this checkout was updated to `7f2581a`, preserving all
local installation evidence. The other stand's F11-F16 are now explicit
comparison points: MSI scaling/clipping, association headers, all-Finish
labels, post-Finish RPC crash, critical-section warnings and synthetic keys.
The association header ellipses were independently observed here (16 screenshot);
record as another environment observation of F12, not a duplicate new defect.
F18 also matters: judge painting by X-server screenshots, not GetPixel alone.
No #27 research DLL/source patch was installed in this stock Wine baseline.

During copy, Photoshop.exe appeared and already matched the expected owner
binary SHA256 `98c746a4707a875f8077d79550f7129b459ae784de05b05f349f89ddecf56d30`
(19533824 bytes). This verifies the file, not installer completion or startup.
`installed-exe.json` explicitly records that the installer was still running.
`dpi-probe.c` is a public-API-only synthetic probe; its DPI-aware result and the
X root size must both be retained rather than assuming identical coordinates.

### Recovery controls and current shared-component stage

`prepare-controls.py` restores six exact Debian MinGW packages using URLs and
SHA256 in toolchain.json, extracts them locally and compiles windows-install,
dpi-probe and product-state (all public APIs). It was run successfully against
verified cached packages during this session. Default paths are the ones in
checkpoint.json; if changing the root, adjust the controller/client constants.

```sh
python3 experiments/cs2-debian-installation/prepare-controls.py
```

At this checkpoint Photoshop.exe is verified, while the standard outer MSI is
still installing its bundled shared components. Bridge was followed by Adobe
Common Files. No Finish click or Photoshop launch is claimed. Later verify the
product with product-state.exe (`MsiQueryProductState` + name/version) and
re-enumerate the final UI before clicking anything; watch F13/F14.

The controller's polling of completed request files consumed avoidable CPU/9p
metadata traffic. Completed request files were moved to completed-requests/,
while response guard files and the full action journal were retained. Keeping
the response guards ensures an in-flight directory iteration still skips old
requests. This is harness bookkeeping, not a Wine/Photoshop fix.

## Completed installer verification (2026-11-08)

The installer progressed through Bridge, Adobe Common Files, Help Center, help
indexing and Stock Photos to the final dialog. F13 reproduced independently:
all final texts, including the caption, read `&Finish` (screenshot28). The
checked optional completion checkbox (id4015, label corrupted) was inspected
with public BM_GETCHECK, unchecked normally, and verified 0. The actual enabled
Finish button (id2003) was then clicked. Its label corruption was not patched.

F14 also reproduced: `Unhandled exception 0x000006a6 in thread 740 ...` and
Program Error: `The program msiexec.exe has encountered a serious problem and
needs to close.` Screenshot30 preserves the error. It was dismissed normally.
A public OpenProcess/WaitForSingleObject/GetExitCodeProcess observer opened
handles before dismissal and captured client1072 exit0 and server1100 exit1;
see msi-exit-status.txt and wait-exit.c. Those IDs are historical.

After dismissal product-state.exe returned 0 and reported:
`state=5 version_status=0 version=9.0 name_status=0 name=Adobe Photoshop CS2`.
State5 is INSTALLSTATE_DEFAULT: the product is registered installed. EXE hash
already matched, but **the installer run was not clean**. No F13/F14 fix has
been made, and no Photoshop launch was yet claimed at this checkpoint.

The later idle controller job reached its 7200-second harness deadline and
powered off its VM. This is not a Photoshop crash. The same installed prefix
and EXE were retained and hash-verified; all old request files were archived
before restarting the controller so stale HWND/button actions could not replay.
No trial state, activation data or clock was reset, and no reinstall occurred.

## First application start checkpoint (2026-11-08 22:10 UTC)

Tracked separately in [#37](https://github.com/unxed/dllmgr/issues/37),
agent `codex-debian-8c42`; this does not claim or start the #35/#36 fixes.
Repository instructions and the other session’s task cards were read through
1818613, including the new claim protocol.

After starting the same retained prefix, public MSI APIs again reported state5,
version9.0. Photoshop was launched from its installation directory at21:58:21
UTC. Its frame and normal Adobe Photoshop CS2 Version9.0 / Tryout Version
splash appeared. At22:10 the splash still says `Looking for preferences…`;
there is no trial continuation dialog or completed workspace yet. The app log
is empty; the process is active and its I/O counters increase. This is evidence
of a delayed startup, not yet proof of a usable editor or a diagnosed hang.
The synthetic settings directory contains a zero-byte Prefs.psp created at
22:00:22; its contents were not inspected or modified.

The reviewed screenshot36 is committed. PID278/Wine PID444 and all HWNDs are
historical observations; enumerate again before interacting. No code patch,
activation workaround, trial reset, hardware change or reinstall was applied.
