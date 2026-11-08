# Wine 57513: no Cyrillic input in PuTTY (IBus) — reproduced, mechanism narrowed

State 2026-11-09 (agent claude-cloud-ada0). Scripts here use absolute
/home/claude/work/putty paths (sandbox); run inside a stand session on its own
prefix, PuTTY from tests/wine/putty085.sh, keylog.exe from tests/wine/keylog.c.

## Setup that matches the owner's desktop (Mint, us,ru, IBus)

- `setxkbmap -layout us,ru`, XKB group locked to 1 with XkbLockGroup and keys
  pressed as physical keycodes through XTest (xkey.py). `xdotool key q` or
  `key Cyrillic_shorti` with a ru-only map are NOT equivalent (xdotool remaps a
  scratch keycode, giving Latin letters or wrong scan codes).
- IBus as XIM server: `ibus-daemon --xim`, engine xkb:us::eng, `XMODIFIERS=@im=ibus`.
- **Locale must be UTF-8** (`LANG=C.UTF-8`): in the C locale XmbLookupString
  cannot return Cyrillic and every app loses the text (false positive).

## Results (PuTTY 0.85 w64, raw connection to a local TCP sink, ime.sh)

| group | IM | bytes received |
|---|---|---|
| us | IBus | `qwe` |
| ru | IBus | nothing (bug) |
| ru | none (`@im=none`) | `йцу` |

## Mechanism so far (WINEDEBUG=+imm,+key)

With IBus the real KeyPress is consumed by the IM; IBus sends a KeyPress with
keycode 0 whose XmbLookupString gives the committed text; winex11 calls
post_ime_update(result) which sends WM_IME_NOTIFY(IMN_WINE_SET_COMP_STRING)
to the default IME window. No WM_KEYDOWN reaches the app (only WM_KEYUP).
- keylog.exe (one window): __wine_ime_wnd_proc forwards the notify to the IME
  UI window (ime_ui_window_proc -> ime_set_comp_string -> ImeToAsciiEx(VK_PROCESSKEY))
  and the app gets WM_IME_COMPOSITION (GCS_RESULTSTR), WM_IME_CHAR, WM_CHAR.
- PuTTY: __wine_ime_wnd_proc receives the same notify but nothing forwards it
  to an IME UI window: no ime_ui_window_proc / ImeToAsciiEx follows, the text
  is dropped. Earlier in the PuTTY trace the IME UI window (0x1006a) got
  WM_DESTROY; PuTTY also calls ImmSetOpenStatus(himc, 0) at startup.
- Tested and ruled out as the sole cause: create+destroy a first top-level
  window before the main one (`keylog.exe first`): text still arrives.
Next: compare what differs (ImmSetOpenStatus 0 on the context, the IME UI
window's owner, ImmAssociateContext); make keylog.exe mimic each PuTTY call
in turn (bisect the PuTTY startup calls seen in the +imm trace).
