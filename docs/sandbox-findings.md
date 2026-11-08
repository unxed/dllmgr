# Sandbox stand findings (deferred)

Problems, error messages and oddities met while building and using the
sandbox stand (docs/sandbox-stand.md). Owner's rule: record them here and fix
them **last**, after the already existing bugs. Newest at the bottom.

| # | Date | Where | Symptom / message | Status |
|---|------|-------|-------------------|--------|
| F1 | 2026-11-08 | Muffin on Xvfb | Aborts: `Settings schema 'org.cinnamon.settings-daemon.peripherals.touchscreen' is not installed` | Worked around: `cinnamon-settings-daemon` in `install` |
| F2 | 2026-11-08 | wineboot, headless | Hangs forever on the invisible Mono download prompt | Worked around: add-on MSIs in Wine's share dir |
| F3 | 2026-11-08 | Sandbox | Detached Xvfb/Muffin killed minutes after a reply | Worked around: `session` per experiment |
| F4 | 2026-11-08 | Xvfb startup | Socket file exists before the server accepts clients; Muffin: `Unable to open display` | Fixed in `session` (polls `xdpyinfo`) |
| F5 | 2026-11-08 | Network | `web.archive.org` resets every connection; plain `http://download.adobe.com` does not resolve | Use the https Adobe URL |
| F6 | 2026-11-08 | wineboot -i, Wine 11.0 | `err:ole:start_rpcss Failed to open/start RpcSs service`, `CoMarshalInterface ... hr 0x80004002`, `err:setupapi:do_file_copyW Unsupported style(s) 0x10` x5, `winebth` service start fails (1359/1062, `c00000e5`) | Open, looks like first-boot noise (no Bluetooth in sandbox); low priority |
| F7 | 2026-11-08 | Any Wine audio init | `ALSA lib ... cannot find card '0'`, `Unknown PCM default` (no sound card in sandbox) | Open, sandbox noise; low priority |
| F8 | 2026-11-08 | Fresh prefix | `LogPixels` is 96 while the owner's stand is 192; installer UI was half size | Fixed: `prefix` sets 192 |
| F9 | 2026-11-08 | CS2 Setup, License Agreement (RichEdit, 192 DPI) | Uneven letter spacing in the EULA text: "AD OBE", wide gaps between words; looks like glyph advance/kerning mismatch | Open, unverified vs. Windows; queue after existing bugs |
| F10 | 2026-11-08 | CS2 Setup.exe | Main 1342x1080 window stays blank white with an inactive title for several seconds before the language picker paints | Open, may be just load time; compare with #36 splash only if relevant |
