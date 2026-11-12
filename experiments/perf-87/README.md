# #87 Performance: startup, file system, thumbnails (measurement only)

Owner, 2026-11-11: make Wine radically faster, start included; this round
only measures. Nothing here changes Wine, the runtime or dllmgr behaviour.

## Tools (tools/perf/; nothing runs unless started)

| Tool | What | Cost |
|---|---|---|
| `startup.py --out DIR --prefix PFX --step REGEX [--do CMD] -- CMD...` | Startup timeline on CLOCK_MONOTONIC (= Wine's `+timestamp` clock): processes of the prefix from /proc every 50 ms (first seen, CPU user/sys), X top-level maps and last screen damage (observer on $DISPLAY), Wine `+timestamp,+loaddll,+process` markers (exe load, helper processes, last DLL load), "quiet" = less than 0.05 CPU-s per `--quiet-ms` over all processes. Output: `timeline.txt`, `summary.json`, `cpu.tsv`, `x.tsv`, `wine.log`. | Wine traces: loader/process lines only; observer polls /proc |
| `startup.py ... --cold PATHS` | evicts PATHS from the page cache first (posix_fadvise DONTNEED, no root; system libraries and fonts stay cached) | |
| `startup.py ... --strace` -> `fs-report.py DIR/fs.strace --prefix PFX [--files REGEX]` | `strace -f -tt -T` of the whole tree: file syscalls per process, syscall, path class, process x class; names asked for in many folders (desktop.ini); directory scans (open + getdents64) and the exact-name miss before each (Wine's case-insensitive fallback); first-open curve of matching files | strace inflates times 5-10x: use counts and shares |
| `startup.py ... --server-trace` -> `server-report.py DIR/server.log` | pre-started `wineserver -f -d1`: round trips per request and per client thread | heavy, counts only |
| `startup.py --live ...` | the owner's own desktop and prefix: measures only, never kills or evicts, refuses to start while something runs in the prefix | as the plain mode |
| `experiments/perf-87/fs-batch.sh`, `ps-batch.sh` | FastStone / Photoshop CS2 run sets (warm, cold, thumbnails, strace, server) in one stand session; `PHASES=` picks | |

Earlier tools reused: DLLMGR_SAMPLE sampler in the dllmgr-27 proxy
(`tools/sample-report.py`), `dllmgr logs`, logs=on (`+loaddll`).
Not usable here: perf and bpftrace (perf_event_paranoid=4, no root).

## Stand (2026-11-12)

Owner's laptop, headless Xvfb :126 3072x1728 192 DPI, Muffin, 4 threads,
other agents running at the same time (load average 3-5 during the runs: the
spread between runs is mostly theirs, disk contention included). Stock =
/opt/wine-stable 11.0 (`wine X.exe` on a prefix without dllmgr); v23 =
private runtime v23 through `dllmgr run` (terminal) or the launch trampoline
(plain `wine X.exe` on a prefix with the recipe: how the owner starts from
the menu). FastStone 8.5 portable, prefix copy of fs40; Photoshop CS2 trial,
copies of ps/prefix-clean. Raw outputs stay on the stand
($B/perf87/out*); numbers below are copied from their timeline.txt.

### FastStone 8.5, start without a folder

| ms from launch | stock warm (3) | stock cold (2) | v23 `dllmgr run` warm | v23 trampoline warm (3) | trampoline cold (2) |
|---|---|---|---|---|---|
| first Wine line | 62-136 | ~70 | 716-860 (best), 1.2-5.1 s under disk load | 70 | 73 |
| FSViewer.exe loaded | 852-944 | | 1894 | | |
| main window mapped | 1216-1356 (2074 under load) | 1529-1811 | 1805-1882 (best), 2.5-6.8 s under load | 2191-2224 | 2900-3783 |
| CPU quiet | 3117-3336 | 3546-3871 | 3293-3864 | 3837-3917 | 5108-5798 |

CPU over a stock warm start (to quiet): FSViewer.exe 1.7 s, wineserver
0.75 s, session helpers 1.2 s (wineboot, services, 2x winedevice, plugplay,
explorer, svchost, rpcss, winemenubuilder): 3.7 CPU-s in 3.2 s.

### FastStone, start into a folder of 100 JPEGs (3000x2000, synthetic)

Quiet at 5.6-6.0 s (stock, thumbnail cache FSIV.db removed or kept alike)
and 5.9-6.2 s (v23), i.e. about +2.4 s over the plain start.
`strace` of a cached run, FSViewer.exe alone: stock 427,290 file syscalls,
3,888 desktop.ini misses each followed by a full listing of Z:\,
Z:\home, Z:\home\unxed (the folder tree walks the real home); v23
(dllmgr-65 shell32 cache) 112,569 syscalls, 46 such scans.

### Photoshop CS2, start to the main window / activation dialog

| ms from launch | stock | v23 `dllmgr run` |
|---|---|---|
| first Wine line | 225 (strace run) | 855 |
| Photoshop.exe loaded | 4771 | 1633 |
| empty grey main window mapped | 5126-11599 | 1895-2742 (10017 under load) |
| fully loaded: "Adobe Activation" (trial over, F25) mapped, warm | 82,499-89,839 | 26,861-31,814 |
| same, cold (Wine, runtime and prefix evicted) | 106,618 | 56,044 |
| first start of a fresh copy: F26 "program error" box (end of loading) | 115,627 | 25,243 |
| CPU to the dialog: Photoshop.exe / wineserver / dllmgr python | 52.5 / 8.9 / - s | 16.4-17.1 / 5.4-6.3 / 2.7 s |

The python CPU is mostly `dllmgr run` copying the traced stderr
(`+process` is chatty for Photoshop); with the default logs=on
(`+loaddll` only) it is smaller. After the dialog the v23 tree idles at
~4.5 % CPU (winedevice.exe 1.5-4.1 CPU-s per run), so "quiet" with the
default threshold is not reached for Photoshop; use `--quiet-cpu 0.2`.

`strace` of a stock start (180 s, not reaching the dialog): 1,475,341
file syscalls, 1,352,915 of them Photoshop.exe; **83,772 desktop.ini
misses, each followed by a full directory listing** (168,670 listings,
337,286 getdents64, 102 MB of directory entries) of C:\, C:\Program Files
(x86), ...\Adobe, ...\Adobe Photoshop CS2, ...\Plug-Ins and its subfolders:
every plug-in path probe makes shell32 look for desktop.ini in each parent
folder. That is #65 in stock Wine (fixed by the dllmgr-65 2 s cache in the
runtime; WineHQ 60739).

`strace` of a v23 start (to the dialog, 174 s traced): 641,867 file
syscalls; desktop.ini down to 1,072 lookups. What is left: Photoshop.exe
300k (component-by-component stats of the paths it opens: "/" 20,871,
"/home" 14,144 ... each parent of the prefix ~14k times), wineserver 218k
(48,742 lookups under Program Files, 40,445 failing), ~/.Xdefaults and
~/.Xdefaults-HOST 30,158 failed opens each (P1), and every helper process
(now also Adobelmsvc.exe, Adobelm_Cleanup) enumerating the system fonts
(6,298 file syscalls each).

### Session start, every app

A fresh wineserver boots the session before the app's exe loads:
wineboot -> winemenubuilder, services, winedevice x2, plugplay, explorer,
svchost, rpcss; FSViewer.exe is loaded at 0.85-0.94 s (stock warm). Each of
these processes enumerates all system fonts on its own (6,302 file
syscalls over 1,585 font paths per process, explorer 12,604; 45,308 of the
116,576 file syscalls of the whole FastStone start, 39 %) and the font
registry (wineserver: 880-1,670 enum_key_value per helper). The stand has
701 fonts, the owner 2,543 (docs/owner-machine.md): this part scales with
his font count.

### wineserver round trips (FastStone stock start, to quiet)

58,911 requests in 3.7 s. FSViewer's main thread 31,859, of them 15,366
for hooks (5,110 hook calls x get_hook_info/start_hook_chain/
finish_hook_chain); registry 6,233 enum_key_value, 4,891 get_key_value,
2,862 open_key over all processes.

### dllmgr's own cost before Wine starts (`dllmgr run`)

cProfile of the launch path, warm: 0.65 s, of it 0.45 s sha256 of the 627
runtime files (`private_runtime.verify`), 0.08 s base Wine files, 0.05 s
the prefix ntdll check, 0.07 s imports. Sampled under the stand's disk load:
1.9 s in the same hashing and once 1.9 s in one write to launch.log; cold:
1.2-2.6 s before the first Wine line. The trampoline path pays it after the
stock session boot.

## Findings (to study after the queue)

- P1 ~/.Xdefaults and ~/.Xdefaults-HOST are opened (and fail) ~10,600 times
  each during a FastStone start and ~15,700 during a folder start, from
  FSViewer.exe's threads: something reloads the X resource database
  repeatedly (Xcursor/Xft per call?).
- P2 `import -window root` under Muffin on the stand returned an all-white
  image for FastStone runs (metacity fine; Photoshop runs fine).
- P3 Lookups of "desktop.ini?" (trailing '?') follow each desktop.ini miss:
  a second wildcard-like probe per folder.
- P4 Photoshop on v23 idles at ~4.5 % CPU after loading (winedevice.exe
  among the busiest).
- P5 Path walks: every parent directory of the prefix is stat'ed ~14k times
  in a Photoshop start (v23), wineserver probes ~49k paths under Program
  Files (most fail): who and why is the next strace question.
- fs-report.py labels lookups relative to the cwd (Wine runs in the server
  directory) as "tmp/run"; read that class as "relative lookups".

## Not measured yet

- Photoshop phase B (Continue Trial -> main window ready) on a fresh copy:
  both variants hit F26 instead of the activation dialog.
- wineserver round trips for Photoshop (only FastStone traced).
- Thumbnail decode cost per image (GDI+/WIC) with DLLMGR_SAMPLE_ALL; real
  camera JPEGs (embedded EXIF thumbnails) instead of synthetic ones.
- Windows CI baseline for the same steps (earlier: FastStone first WM_NULL
  reply 730 ms on the Windows runner, docs/faststone.md).
- The owner's machine (queued command below).

## Owner's machine (queued in #87, not asked yet)

Close FastStone and Photoshop, then:

    cd ~/dev/dllmgr && git pull -q && mkdir -p ~/dllmgr-perf
    python3 tools/perf/startup.py --live --out ~/dllmgr-perf/faststone --prefix ~/.wine --wine-log "$HOME/.wine/.dllmgr/runs/*.log" --step '^FastStone.Image.Viewer' -- dllmgr run faststone
    # close FastStone, then:
    python3 tools/perf/startup.py --live --out ~/dllmgr-perf/photoshop --prefix ~/.wine --wine-log "$HOME/.wine/.dllmgr/runs/*.log" --step 'Adobe Activation|^Adobe Photoshop$' --timeout 240 -- dllmgr run photoshop-cs2

It prints the timeline; ~/dllmgr-perf holds the files to send.
