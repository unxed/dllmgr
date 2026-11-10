# The owner's machine (reference for reproductions)

From the owner's sysinfo dump, 2026-11-10 (only the facts that matter for
rendering and timing; the dump itself is not stored in the repo).

- Linux Mint 22.3, Cinnamon on X11; LANG=ru_RU.UTF-8 (all LC_* Russian).
- Intel HD Graphics 520 (Skylake, Mesa), 4 CPU threads, 15 GiB RAM.
- Laptop panel eDP-1, **native 1920x1080 (344 x 194 mm, ~142 DPI)**, but
  the X screen is **3072x1728**: Cinnamon's fractional scaling renders at 2x
  and xrandr scales the framebuffer down by 0.625 to the panel.
  Consequences: everything we draw at 192 DPI (Xft.dpi 192, Wine LogPixels
  192) is resampled to 1920x1080 before it reaches the eye; screenshots
  (3072x1728) are not what the owner sees. Crisp 1-px detail at 2x becomes
  0.625-px detail; pixel-exact comparisons should also be checked after a
  0.625 downscale.
  How it is set (owner's screenshot of Cinnamon "Display", 2026-11-10):
  Resolution 1920 x 1080 (16:9), 60.02 Hz, landscape, **Monitor scaling
  125 %** (choices 75/100/125/150/175/200 %). Cinnamon implements a
  fractional 125 % on X11 as integer UI scale 2 (Xft.dpi 192, GDK scale 2)
  plus an xrandr transform that makes the X screen 1920 * 1.6 = 3072 wide
  and scales it back by 1/1.6 = 0.625 to the panel: 2 * 0.625 = 1.25.
  Any Mint user who picks 125/150/175 % gets this kind of setup.
- Xft: antialias 1, hinting 1, hintslight, rgba rgb; text-scaling-factor 1.0.
- Cursor theme Bibata-Modern-Classic, size 24 (#44 theme matching).
- 2543 fonts (fc-list), the stand has 701 (#70).
- Photoshop CS2 usually started through the launch trampoline (watched run).
