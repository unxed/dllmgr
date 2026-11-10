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
