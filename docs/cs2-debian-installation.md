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
   Extraction in progress; no completion or installation result claimed yet.

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
| D5 | Self-extractor first screenshot | First frame was black while the X window was already present; the next stable screenshot painted the WinZip UI | Readiness/timing observation under CPU emulation. A transient screenshot is not proof of a persistent paint defect. |

Wineboot and extraction are distinct from MSI installation and from the
installed application's first trial launch. Track their outcomes separately.
