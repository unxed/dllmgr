# PuTTY under Wine (#20)

Pinned build: PuTTY 0.85 (2026-08-16), official putty.exe, fetched and
verified by tests/wine/putty085.sh (w64 d01fdb5a…, w32 4c70267c…).

## Wine bugs (audit 2026-11-09, quicksearch "putty", PuTTY-related only)

| Bug | Title | Last confirmed | Symptom | Offline repro? |
|---|---|---|---|---|
| 57513 | Keyboard input is unavailable in Russian keyboard layout in putty | Wine 11, PuTTY latest (owner, 2026-11-07) | Cyrillic keys type nothing; English works. Comments: with IBus no X11DRV_KeyEvent is logged for Cyrillic keys; `XMODIFIERS=@im=xim` works around it (same for SketchUp, German umlauts) | yes: IBus in Xvfb + local raw TCP server receiving the typed bytes |
| 7007 | putty 0.60 window does not resize when wm resizes it | 2024 (bug touched) | window size not following WM resize | yes, xdotool windowsize |
| 22872 | PuTTY Pageant authentication agent does not provide cached keys | 2017 | Pageant keys not used by PuTTY | needs local sshd (ask before) |
| 38690 | corrupted serial communications | 2023 | serial data corrupted (PuTTY serial) | no: needs a serial device (a pty pair may do) |
| 19286 | puTTy connection manager: two UI bugs | 2016 | third-party PuTTY CM, not PuTTY | out of scope |
| 1151 | stock fixed fonts proportional | 2020 | gdi32 stock fonts; affects terminal look of old apps | maybe, check if PuTTY uses them |
Dropped (not PuTTY): 48678, 50591, 52154, 40322, 43666 (winegcc build).

Priority: 57513 (owner: critical).

57513 status: reproduced on the sandbox stand (IBus + us,ru, UTF-8 locale), mechanism narrowed to the IME notification not reaching an IME UI window in PuTTY; details and scripts in experiments/putty-57513/README.md.
