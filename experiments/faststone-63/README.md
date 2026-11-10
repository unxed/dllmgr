# #63: FastStone path combo, drop-down button without a left side

The owner's screenshot is FastStone's path combo (path row, right end, next
to the jar icon), not Photoshop (issue title corrected).

From the #21 CI captures (run 42415777621, 96 DPI, same 481x24 combo),
windows-vs-wine96-themed-classic.png, left to right: Windows themed normal
(arrow only, no frame), Windows themed hover (full frame, left line
highlighted), Wine themed normal (grey frame on top/right/bottom only: the
owner's look), Wine themed hover (blue frame, again no left side), Windows
classic.

Wine's light.msstyles [ComboBox.DropDownButton] normal image is a full grey
rounded rectangle (blue_combobox_dropdownbutton.svg, stroke #aeaeae); its
left column is covered in this combo (the edit child overlaps the button's
left edge), so only three sides show. Windows' normal state draws no frame
at all.

Options (not done, needs the owner's choice, the theme file is prefix-wide):
1. normal state without a frame, like Windows (light.msstyles image change;
   affects every themed combo in the prefix);
2. find why the left column is covered (combo/edit geometry in Wine's
   comctl32 v6 combo) and keep Wine's look with all four sides.

## 2026-11-10 20:40: option 1 (owner's choice), patches/dllmgr-63.patch

Owner chose the Windows look. Instead of editing the prefix-wide
light.msstyles, the fix lives in our private comctl32_v6 (FastStone only):
COMBO_ThemedPaint draws the drop button with CP_DROPDOWNBUTTONRIGHT when the
theme defines it, like Windows since Vista. Wine's light.msstyles already has
[ComboBox.DropDownButtonRight] with no frame in the normal state.
(The path box is not CBF_EDIT on our side: a first try limited to editable
combos had no effect.)

Stand (t63.sh, `dllmgr run` environment, private comctl32 swapped through
DLLMGR_COMCTL32; dllmgr63-before-after-zoom.png, top faststone-v4, bottom
the patch, left normal, right hot):
- normal: no button frame, only the glyph, as on Windows. Done.
- hot: the blue frame still lacks its left side: the button starts at
  x=2666 (CBCalcPlacement: button 1580..1614 in the 1616 px combo), the blue
  frame is visible from x=2669; the first 2-3 columns of the button are
  covered by something drawn later. Open.
Not shipped yet: needs a catalog fix entry and a faststone-v5 module release.

## 2026-11-10 21:30: hover left side fixed (button geometry like Windows)

Child-window probe (tests/wine/kids63.c, EnumChildWindows of the main
window): the path box is a TTntComboBox (CBS_DROPDOWNLIST | owner-draw
fixed | has strings) with a TTntEdit sibling on top; the edit ends before
the button, so it is not what covers it.

Experiments in our comctl32_v6 (env switches, not shipped):
- button painted after the text field: no change;
- no WM_DRAWITEM to the owner: no change;
- button rect left + 6: the blue left line appears at +6.
So FastStone paints the text field itself up to client width -
SM_CXVSCROLL, after the combo has painted. Wine's button is
[width - 2 - SM_CXVSCROLL, width - 2): its first 2 columns (192 DPI) lie
under that paint. Windows (themed, #21 capture at 96 DPI): the button is
[width - SM_CXVSCROLL, width - 1), the left line right after FastStone's
field, and the 1 px theme border at width - 1.

patches/dllmgr-63.patch now also sets that geometry in CBCalcPlacement for
themed combos. Stand (t63.sh, dllmgr63-before-after-zoom.png, top
faststone-v4, bottom the patch; left normal, right hot): normal shows only
the glyph, hot has the full blue frame, as on Windows.
Not covered: theme switched on a live combo keeps the old geometry until
the next resize; Wine's comctl32 combo tests check no horizontal geometry.
