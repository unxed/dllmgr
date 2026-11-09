# #65 long "Scanning for plug-ins" at start

Stand (2026-11-10, runtime v10, dllmgr run): scan-time.sh samples the
splash status line every 2 s: "Scanning for plug-ins..." from ~6 s to
~21 s (15 s), then Initializing / Reading color settings / Starting-up
plug-ins, trial dialog at ~30 s. Module-load timestamps: a 13.6 s gap with
no loads before PLUGIN.dll.

scan-strace.sh, 8 s of the scan: Photoshop.exe 18,855 openat, 18,830
getdents64, 26,516 newfstatat (14,124 failing), 4,720 writev; wineserver
mostly idle. The time goes to file system lookups (directory listings),
not to the server. Next: which paths, and why each needs a directory
listing (case-insensitive lookup misses?).

The 60 s RtlpWaitForCriticalSection 01502750 warning (owner's log and the
stand) is a worker waiting while the main thread is in the trial dialog;
not the scan itself.
