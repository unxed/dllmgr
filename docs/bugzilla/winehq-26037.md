# Draft: follow-up to WineHQ bug 26037 "Tahoma Bold is not bold"

Status: draft, not posted. The owner posts it. Gate (docs/faststone.md): the
observation is reproduced (stock Wine 11.0 font files, owner's screenshot);
the "passes with only the change" part waits for a corrected font.
Words only: no code and no links to code (D20).

---

Tahoma Bold is still not bold for most Cyrillic letters in Wine 11.0.

In Wine 11.0's fonts/tahomabd.ttf, Cyrillic letters that share their shape
with a Latin letter are bold (а, с, о, р, е have 1.65–1.88 times the outline
area of the same letters in tahoma.ttf, like Latin x at 1.65). All other
Cyrillic letters we checked (Ф й л д ш у П в т з м ы к) have exactly the same
outline area as in tahoma.ttf (ratio 1.00): they use the regular outlines,
but with the wider advance widths of the bold face. Both fonts contain every
letter, so this is not a missing-glyph fallback.

Visible result: a bold Russian heading mixes bold and regular letters, with
gaps after the regular ones. Seen in FastStone Image Viewer 8.5 (fullscreen
left panel headings "Файл, слайдшоу", "Поворот, размеры, текст"), Wine 11.0
from winehq-stable, 192 DPI. Rendering the same strings directly with
tahomabd.ttf shows the same pattern, so it is the font data, not GDI.

How it was measured: for each letter, the area enclosed by the glyph outline
in tahomabd.ttf was divided by the area of the same letter in tahoma.ttf.

Expected: every Cyrillic letter in tahomabd.ttf has bold outlines, as in
Windows' Tahoma Bold, with advance widths that match those outlines.

This report was prepared with an AI agent (fix-it-in-wine).
