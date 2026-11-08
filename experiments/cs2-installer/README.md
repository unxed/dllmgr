# CS2 installer: F13 ("&Finish" everywhere) and F14 (msiexec 0x6a6)

Opus notes 2026-11-08 (data from the MSI only, no code reverse engineering).

Tables exported with Wine's own tool:
`wine msidb -d "<...>\Adobe Photoshop CS2.msi" -f <dir> -e Dialog Control ControlEvent`
(the same dialog exists in `Adobe Common File Installer.msi`).

Final dialog `SetupCompleteSuccess` (374x266 DLU, title `[ProductName] -
Setup`, default/cancel control `OK`) defines distinct texts: TextLine1
"InstallShield Wizard Completed", TextLine2/3 install/uninstall sentences,
UpdateTextLine1-3, LaunchProgramText "Launch the program", LaunchReadmeText
"Show the readme file", CheckForUpdatesText, buttons Back "< &Back",
OK "&Finish", Cancel; checkboxes CheckLaunchProgram/CheckLaunchReadme
(properties LAUNCHPROGRAM/LAUNCHREADME), CheckBoxUpdates
(ISCHECKFORPRODUCTUPDATES); Bitmap `Image` = NewBinary26. OK's events:
EndDialog Exit, DoAction CheckForProductUpdates(OnReboot) under conditions.

So the window title and every control showing "&Finish" (screenshot F13) is
produced by Wine, not by the package: "&Finish" is OK's own text.
Log next to it: `fixme:msi:internal_ui_handler internal UI not implemented
for message 0x0b000000 (UI level = 5)` x2. 0x0B000000 is
INSTALLMESSAGE_COMMONDATA (installers use it to change e.g. the dialog
caption). Candidate mechanism, **not proven**: a COMMONDATA (or text
formatting) path in Wine's msi dialog code applies one string to the whole
dialog. Also `Failed to load bitmap (null)` x3: the Bitmap control's binary
lookup fails.

Next steps (cheap first): `WINEDEBUG=+msi` around the final dialog only
(grep dialog/control creation and the COMMONDATA record fields); compare
with the same dialog on Windows (PS-1 CI job screenshots). F14 (0x6a6
RPC_S_INVALID_BINDING after QueryServiceObjectSecurity /
SetServiceObjectSecurity semi-stubs) is a separate path: likely a custom
action configuring a service; relates to Wine 53571 (installer custom action
page fault). Priority: below the runtime crashes (docs/photoshop-wine-audit.md
work order item 6); installation completes despite both.

## F13 run 1 (2026-11-09, agent claude-cloud-ada0)

Fresh 192 DPI prefix, `scripts/sandbox-install-cs2.sh` with
`WINEDEBUG=+relay,+msi` and RelayInclude limited to
user32.SetWindowText[AW]/SetDlgItemText[AW] (log 45 MB, kept locally in
/home/claude/work/f13/install-run1.log). Result:
- The "&Finish everywhere" dialog is **not** Wine's internal MSI dialog: it
  belongs to Adobe's custom action `CA_InstallFinishDisplay` (type 41,
  NewBinary20!PerformSubInstalls), running in the custom-action process
  (thread with `__wine_msi_call_dll_function`). Its own dialog proc
  (WM_INITDIALOG at 10017B98, module based at 0x10000000) calls
  SetDlgItemTextA for every control id (0x7d3, 0x7d2, 2, 0xfa1, 0xfaf,
  0xfa0, 0xfa3) and SetWindowTextA for the caption, always from the same
  buffer, which holds "&Finish".
- No MSI API trace in that thread between those calls; meanwhile the main
  process answers remote property queries (`SELECT Value FROM _Property
  WHERE _Property=?`).
- Checked in source and ruled out: MsiGetPropertyA remote path with an empty
  value writes the terminating NUL (msi_strncpyWtoA), so "stale buffer after
  an empty property" is not it in the simple form.
Next (run 2): relay all msi exports plus LoadStringA, GetDlgItemTextA,
GetPrivateProfileStringA, lstrcpyA, FindResourceA to see where the strings
come from.
