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
