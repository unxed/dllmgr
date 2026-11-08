# Wine 11412 (CS2 palettes / submenus) on Muffin, sandbox retest

2026-11-08, stock Wine 11.0, Xvfb 3072x1728 @192 DPI, **Muffin** (the owner's
Cinnamon WM; compositing), CS2 Tryout from scripts/sandbox-install-cs2.sh.
Complements the owner's Metacity retest (Wine 11412 c25, not reposted).

1. Blur/Sharpen/Smudge flyout (right click on the Blur tool in Tools):
   the submenu is drawn **above** the Tools palette (the #34135 symptom,
   submenu behind the palette, does not occur).
2. A large native X client (xlogo) activated over Photoshop covers the main
   window and every palette part under it; palettes do not stay on top.
3. Alt+Tab works under Muffin (XTest key events): xlogo -> Photoshop
   (palettes above its main window) -> xlogo (palettes covered again; the
   screen equals the step-2 capture except for small window-decoration
   differences).

So the #34136 "palettes stay on top after switching" symptom is not seen with
Metacity or Muffin, including real Alt+Tab switching on Muffin. Not covered:
workspaces, other WMs (KWin, Xfwm), Wayland. Nothing posted to WineHQ.
