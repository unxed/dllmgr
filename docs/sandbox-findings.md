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
| F11 | 2026-11-08 | CS2 InstallShield MSI dialogs, 192 DPI | MSI wizard windows stay 623x443 (not DPI-scaled) while fonts are 192 DPI: titles clipped ("Adobe Photoshop CS2" cut off), branding text "InstallShi…", wrapped lines cut | Open; likely Wine msi dialog DPI scaling; queue after existing bugs |
| F12 | 2026-11-08 | CS2 Setup "File Association" page (Adobe custom dialog, 996x681) | List view column headers PS/IR/NC collapse to "…": column widths not DPI-scaled | Open |
| F13 | 2026-11-08 | CS2 MSI final dialog | Every control text, the title too, reads "&Finish" (labels, checkbox, all three buttons); log: `err:msi:dialog_bitmap_control Failed to load bitmap (null)` x3, `fixme:msi:internal_ui_handler internal UI not implemented for message 0x0b000000 (UI level = 5)` x2 | Open; real-looking Wine msi bug; screenshot kept locally as f13-finish.png |
| F14 | 2026-11-08 | msiexec after clicking Finish | `wine: Unhandled exception 0x000006a6 in thread 348` (RPC_S_INVALID_BINDING raised) right after `QueryServiceObjectSecurity`/`SetServiceObjectSecurity` semi-stubs; "Program Error: msiexec.exe"; Photoshop.exe was already installed (SHA256 matches) | Open |
| F15 | 2026-11-08 | Photoshop CS2 first start | `err:sync:RtlpWaitForCriticalSection section 01502750 "?" wait timed out in thread 0174, blocked by 0024` repeating; UI stays responsive | Open |
| F16 | 2026-11-08 | Photoshop CS2 main window, xdotool | `xdotool windowactivate --sync W key ctrl+q` is ignored; mouse menu File + `x` exits cleanly (exit 0). Keyboard focus/input path vs. synthetic keys unclear | Open; test harness or Wine focus issue, unverified |
| F17 | 2026-11-08 | Stand, Muffin | Muffin composites (mutter); screen-DC `GetPixel` then lags/reads white: the #27 popup test gave underlay `ffffff` instead of `f0cc5a`. Docs wrongly said "no compositing" | Fixed: `STAND_WM=metacity` (`--compositor=none`) reproduces the owner's popup-pump-wine.txt exactly |
| F18 | 2026-11-08 | Wine 11.0 screen DC | `GetPixel(GetDC(NULL))` after an X Expose that Wine did not flush returned the window surface colour (f0cc5a) while the X server showed black: screen-DC sampling can disagree with what is on screen. Matters for probes (first-open-probe, window-first-paint) | Open; occlusion gate now judges by X pixels (`import`) |
