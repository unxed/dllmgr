# #87 Performance: startup, file system, thumbnails (measurement only)

Tools (tools/perf/, off unless run; they change nothing in Wine or dllmgr):

- `startup.py --out DIR --prefix PFX --step REGEX [--cold PATHS] [--strace] -- CMD`:
  startup timeline (process first seen, X maps, Wine +timestamp loads,
  CPU-quiet, last screen damage) and CPU per process name.
- `fs-report.py DIR/fs.strace --prefix PFX [--files REGEX]`: file syscalls per
  process, syscall, path class; per-folder lookups (desktop.ini); directory
  scans after exact-name misses; first-open curve of matching files.
- `fs-batch.sh` (here): FastStone warm/cold/thumbnail/strace runs in one
  stand session.

Results: see below (in progress).
