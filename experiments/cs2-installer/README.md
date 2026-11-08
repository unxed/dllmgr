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

## F13 run 2 (2026-11-09)

Relay of kernel32/user32 string functions (msi relay did not engage: a
RelayInclude entry without a dot is a function name; use `msi.*`). The
custom action DLL is extracted as `msicd3d.tmp` (base 0x10000000). Its first
dialog (resource 0x7d0, progress) gets correct, distinct texts ("InstallShield
Wizard Completed" probe, "&Finish", "<&Back", "&Cancel", "Installing Adobe
Photoshop CS2...", "Status:"); for the final dialog (resource 0x7d1) only the
first SetDlgItemTextA ("&Finish" for 0x7d3) has a fresh string, every later
control and the caption reuse the same buffer unchanged. FindResourceA(…,
type 0xf0 RT_DLGINIT) fails for both dialogs (also for the working one, so
not the cause). No GetPrivateProfileString/LoadString/msi trace in that
thread except MsiGetMode; note MsiGetPropertyA has no TRACE in Wine 11.0, so
remote property reads (served by `SELECT Value FROM _Property` in the main
process) are invisible without msi.* relay.
Current hypothesis (not proven): the texts are read with MsiGetPropertyA and
a later remote call fails, leaving the caller's buffer untouched. Run 3:
RelayInclude `msi.*`.

## F13 + F14 mechanism, proven (run 3, 2026-11-09)

RelayInclude `msi.*` (log 45 MB, local /home/claude/work/f13/install-cs2.log):
1. Adobe's custom action CA_InstallFinishDisplay (NewBinary20!PerformSubInstalls)
   runs in the custom-action host process; its remote MSI calls go through the
   host's process-global RPC binding to the installing msiexec. Its last
   successful MsiGetPropertyA is before the sub-installs.
2. The same custom action then runs nested installs in that process:
   `MsiSetInternalUI(2)` + `MsiInstallProductA("...\Bridge\Adobe Bridge 1.0.msi",
   "ARPSYSTEMCOMPONENT=1 REBOOT=ReallySuppress ...")` and more.
3. Back in the final dialog, every MsiGetPropertyA ("FINISHTEXT", "BACKTEXT",
   "CANCELTEXT", "DIALOGTEXT2", "WINDOWTITLE", "LAUNCHTEXT", ...) returns
   0x6A6 RPC_S_INVALID_BINDING; the caller's buffer keeps the last good value
   "&Finish", which the CA puts on every control and the caption (F13).
   The main install thread is still waiting for the CA (session alive), so the
   binding was not lost because the session ended.
4. Wine 11.0 source: MSI_FreePackage (dlls/msi/package.c) calls
   `RpcBindingFree(&rpc_handle)` on the process-global custom-action client
   binding (created in __wine_msi_call_dll_function, dlls/msi/custom.c)
   whenever any package is freed. Freeing the nested install's package in the
   custom-action host therefore destroys the outer custom action's binding.
   The later msiexec crash with unhandled 0x6A6 after Finish (F14) is the same
   invalid binding raised from a remote call (exception code matches).
Fix idea (for WineHQ, words only): a package created inside a custom-action
host must not free the host's client binding; free it only when the host
finishes (or keep it per custom action). Impact: cosmetic final dialog plus a
crash after installation completes; Photoshop is installed correctly.
