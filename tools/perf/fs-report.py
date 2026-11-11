#!/usr/bin/env python3
"""File system cost of a Wine run from `strace -f -tt -T` output (#87).

usage: fs-report.py FS.STRACE [--prefix PREFIX] [--top N] [--files REGEX]
                    [--from-s S] [--to-s S]

FS.STRACE is what tools/perf/startup.py --strace writes (or any
`strace -f -tt -T -e trace=%file,getdents64,clone,clone3,vfork,fork,prctl,
ioctl,close,execve`). Prints:
  - per process: file syscalls, failures, summed syscall time;
  - per syscall and per path class (prefix system32, fonts, app dir, Wine
    install, system libraries, ...);
  - per-folder lookups: names asked for in many directories (desktop.ini,
    ...), with the directory scans they caused;
  - directory scans (open of a directory + getdents64 until the end): how
    many, of which directories, and the failed lookup that preceded each
    one (Wine's case-insensitive fallback after an exact-name miss);
  - --files REGEX: first open of every matching file (e.g. the images of a
    thumbnail folder), as a progress curve.
Times measured under strace are inflated (ptrace stops); compare counts and
shares, take totals from untraced runs.
"""
import argparse, collections, os, re, sys

LINE = re.compile(r'^(\d+)\s+(\d\d):(\d\d):(\d\d\.\d+)\s+(.*)$')
CALL = re.compile(r'^(\w+)\((.*)\)\s+=\s+(-?\d+|0x[0-9a-f]+|\?)(?:\s+(E\w+)\s+\([^)]*\))?.*?(?:<(\d+\.\d+)>)?\s*$')
STR = re.compile(r'"((?:[^"\\]|\\.)*)"')
FILE_CALLS = {'open', 'openat', 'openat2', 'stat', 'lstat', 'newfstatat', 'fstatat64', 'statx', 'access',
              'faccessat', 'faccessat2', 'readlink', 'readlinkat', 'getdents64', 'mkdir', 'mkdirat', 'unlink',
              'unlinkat', 'rename', 'renameat', 'renameat2', 'chdir', 'statfs', 'truncate', 'utimensat',
              'chmod', 'fchmodat', 'symlink', 'symlinkat', 'link', 'linkat', 'rmdir', 'inotify_add_watch',
              'execve', 'getxattr', 'lgetxattr', 'listxattr', 'llistxattr'}
PER_FOLDER = ('desktop.ini', 'thumbs.db', 'folder.jpg', 'autorun.inf', 'ehthumbs.db', 'folder.gif')


def unescape(s):
    try:
        return s.encode('latin-1', 'backslashreplace').decode('unicode_escape').encode('latin-1').decode('utf-8', 'replace')
    except Exception:
        return s


def classify(path, prefix):
    low = path.lower()
    base = low.rsplit('/', 1)[-1]
    if base == 'desktop.ini':
        return 'desktop.ini'
    if base in PER_FOLDER:
        return 'per-folder metadata'
    if prefix and path.startswith(prefix):
        rel = low[len(prefix):]
        for key, name in (('/drive_c/windows/system32', 'prefix system32'),
                          ('/drive_c/windows/syswow64', 'prefix syswow64'),
                          ('/drive_c/windows/fonts', 'prefix fonts'),
                          ('/drive_c/windows', 'prefix windows (other)'),
                          ('/drive_c/program files', 'prefix Program Files'),
                          ('/drive_c/users', 'prefix user profile'),
                          ('/dosdevices', 'prefix dosdevices'),
                          ('/drive_c', 'prefix drive_c (other)')):
            if rel.startswith(key):
                return name
        if rel.endswith('.reg'):
            return 'prefix registry files'
        return 'prefix (other)'
    if '/dllmgr/runtimes/' in path or path.startswith('/opt/wine'):
        if '/share/fonts' in low or low.endswith(('.ttf', '.ttc', '.otf', '.fon')):
            return 'Wine install fonts'
        if '/nls/' in low or low.endswith('.nls'):
            return 'Wine install nls'
        return 'Wine install (lib)'
    if 'fontconfig' in low or '/fonts/' in low or low.endswith(('.ttf', '.ttc', '.otf', '.pfb', '.pcf.gz')):
        return 'system fonts'
    if low.startswith(('/usr/lib', '/lib', '/usr/local/lib', '/etc/ld.so')):
        return 'system libraries'
    if low.startswith(('/proc', '/sys', '/dev')):
        return 'proc/sys/dev'
    if low.startswith('/tmp') or low.startswith('/run'):
        return 'tmp/run (sockets)'
    if low.startswith('/etc'):
        return 'etc'
    if low.startswith('/usr/share'):
        return 'usr/share (other)'
    return 'other'


class Stat:
    __slots__ = ('n', 'fail', 'time', 'paths')

    def __init__(self):
        self.n = self.fail = 0
        self.time = 0.0
        self.paths = set()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('trace')
    ap.add_argument('--prefix', default='')
    ap.add_argument('--top', type=int, default=15)
    ap.add_argument('--files', default='')
    ap.add_argument('--from-s', type=float, default=0)
    ap.add_argument('--to-s', type=float, default=1e9)
    a = ap.parse_args()
    prefix = os.path.realpath(a.prefix) if a.prefix else ''
    tgid, comm, fds, cwd = {}, {}, {}, {}
    pending = {}
    t_first = None
    per_proc = collections.defaultdict(Stat)
    per_call = collections.defaultdict(Stat)
    per_class = collections.defaultdict(Stat)
    name_dirs = collections.defaultdict(set)   # basename -> dirs asked in (lookups that failed or not)
    name_stat = collections.defaultdict(Stat)
    last_miss = {}  # tid -> path of the last ENOENT lookup
    scans = {}      # (pid, fd) -> [dir, calls, bytes, t, cause]
    scan_done = []  # (dir, calls, bytes, cause, proc)
    fail_paths = collections.Counter()
    first_open = {}
    files_re = re.compile(a.files, re.I) if a.files else None
    total = Stat()

    def proc_of(tid):
        return tgid.get(tid, tid)

    def resolve(pid, args_dirfd, path):
        if path.startswith('/'):
            return path
        if args_dirfd is not None and args_dirfd != 'AT_FDCWD':
            base = fds.get((pid, args_dirfd))
            if base:
                return base.rstrip('/') + ('/' + path if path else '')
        return os.path.join(cwd.get(pid, ''), path) if cwd.get(pid) else path

    def finish_scan(key):
        s = scans.pop(key, None)
        if s and s[1]:
            scan_done.append((s[0], s[1], s[2], s[4], comm.get(key[0], str(key[0]))))

    with open(a.trace, errors='replace') as f:
        for raw in f:
            m = LINE.match(raw)
            if not m:
                continue
            tid = int(m.group(1))
            t = int(m.group(2)) * 3600 + int(m.group(3)) * 60 + float(m.group(4))
            body = m.group(5)
            if body.endswith('<unfinished ...>'):
                pending[tid] = body[:-len('<unfinished ...>')].rstrip()
                continue
            r = re.match(r'^<\.\.\. (\w+) resumed>(.*)$', body)
            if r:
                head = pending.pop(tid, r.group(1) + '(')
                body = head + r.group(2)
            if body.startswith(('+++', '---')):
                if body.startswith('+++') and tid == proc_of(tid):
                    for key in [k for k in scans if k[0] == tid]:
                        finish_scan(key)
                continue
            if t_first is None:
                t_first = t
            rel = t - t_first
            c = CALL.match(body)
            if not c:
                continue
            call, args, ret, err, dur = c.group(1), c.group(2), c.group(3), c.group(4), c.group(5)
            dur = float(dur) if dur else 0.0
            pid = proc_of(tid)
            try:
                rv = int(ret, 0)
            except ValueError:
                rv = None
            # process bookkeeping
            if call in ('clone', 'clone3', 'fork', 'vfork') and rv and rv > 0:
                if 'CLONE_THREAD' in args:
                    tgid[rv] = pid
                else:
                    tgid[rv] = rv
                    comm[rv] = comm.get(pid, '?')
                    cwd[rv] = cwd.get(pid, '')
                    for (p, fd), path in list(fds.items()):
                        if p == pid:
                            fds[(rv, fd)] = path
                continue
            if call == 'prctl' and 'PR_SET_NAME' in args and tid == pid:
                s = STR.search(args)
                if s:
                    comm[pid] = unescape(s.group(1))
                continue
            if call == 'execve' and rv == 0:
                strs = [unescape(x) for x in STR.findall(args)]
                exe = strs[0] if strs else '?'
                name = os.path.basename(exe)
                if 'wine' in name:
                    exes = [x for x in strs[1:6] if x.lower().endswith('.exe')]
                    name = exes[0].replace('\\', '/').rsplit('/', 1)[-1] if exes else name
                comm[pid] = name
                for key in [k for k in fds if k[0] == pid]:
                    pass  # CLOEXEC unknown; keep
            if call == 'close' and rv == 0:
                fd = args.strip()
                finish_scan((pid, fd))
                fds.pop((pid, fd), None)
                continue
            if call == 'chdir' and rv == 0:
                s = STR.search(args)
                if s:
                    cwd[pid] = resolve(pid, None, unescape(s.group(1)))
            if call == 'ioctl' or call not in FILE_CALLS:
                if call == 'ioctl':
                    st = per_call['ioctl (all)']
                    st.n += 1
                    st.time += dur
                    st.fail += rv is not None and rv < 0
                continue
            if not (a.from_s <= rel <= a.to_s):
                continue
            # path
            if call == 'getdents64':
                fd = args.split(',', 1)[0].strip()
                path = fds.get((pid, fd), '<fd %s>' % fd)
                key = (pid, fd)
                if key not in scans:
                    miss = last_miss.get(tid)
                    cause = miss if miss and os.path.dirname(miss) == path.rstrip('/') else ''
                    scans[key] = [path, 0, 0, t, cause]
                if rv:
                    scans[key][1] += 1
                    scans[key][2] += max(rv, 0)
                else:
                    scans[key][1] += 1
                    finish_scan(key)
            else:
                strs = STR.findall(args)
                if not strs:
                    continue
                first_arg = args.split(',', 1)[0].strip()
                dirfd = first_arg if call.endswith('at') or call in ('statx', 'openat2', 'faccessat2', 'renameat2') else None
                path = resolve(pid, dirfd, unescape(strs[0]))
                if call in ('open', 'openat', 'openat2') and rv is not None and rv >= 0:
                    fds[(pid, str(rv))] = path
                    if files_re and files_re.search(path) and path not in first_open:
                        first_open[path] = rel
            failed = rv is not None and rv < 0
            if failed and err == 'ENOENT':
                last_miss[tid] = path
                fail_paths[path] += 1
            cls = classify(path, prefix)
            for st in (per_proc[comm.get(pid, str(pid))], per_call[call], per_class[cls], total):
                st.n += 1
                st.fail += failed
                st.time += dur
                st.paths.add(path)
            if call != 'getdents64':
                base = os.path.basename(path).lower()
                if base:
                    name_dirs[base].add(os.path.dirname(path).lower())
                    ns = name_stat[base]
                    ns.n += 1
                    ns.fail += failed
                    ns.time += dur
    for key in list(scans):
        finish_scan(key)
    span = (t - t_first) if t_first is not None else 0

    def table(title, rows, key=lambda kv: -kv[1].time, limit=None):
        print('\n## ' + title)
        print('%-40s %8s %8s %9s %8s' % ('', 'calls', 'failed', 'time ms', 'paths'))
        for name, st in sorted(rows.items(), key=key)[:limit or a.top]:
            print('%-40s %8d %8d %9.1f %8d' % (str(name)[:40], st.n, st.fail, st.time * 1000, len(st.paths)))

    print('# %s: %.1f s traced, %d file syscalls (%d failed), %.0f ms in them (strace-inflated)' % (
        a.trace, span, total.n, total.fail, total.time * 1000))
    table('per process', per_proc)
    table('per syscall', per_call)
    table('per path class', per_class, limit=40)
    print('\n## per-folder lookups: names asked for in the most directories')
    print('%-28s %6s %8s %8s %9s %7s' % ('name', 'dirs', 'calls', 'failed', 'time ms', 'scans'))
    caused = collections.Counter(os.path.basename(s[3]).lower() for s in scan_done if s[3])
    for name, dirs in sorted(name_dirs.items(), key=lambda kv: -len(kv[1]))[:a.top]:
        st = name_stat[name]
        print('%-28s %6d %8d %8d %9.1f %7d' % (name[:28], len(dirs), st.n, st.fail, st.time * 1000, caused[name]))
    for name in PER_FOLDER:
        if name in name_stat and name not in dict(sorted(name_dirs.items(), key=lambda kv: -len(kv[1]))[:a.top]):
            st = name_stat[name]
            print('%-28s %6d %8d %8d %9.1f %7d' % (name, len(name_dirs[name]), st.n, st.fail, st.time * 1000, caused[name]))
    print('\n## directory scans (open + getdents64 to the end): %d scans, %d getdents64 calls, %.1f MB of entries' % (
        len(scan_done), sum(s[1] for s in scan_done), sum(s[2] for s in scan_done) / 1e6))
    after_miss = [s for s in scan_done if s[3]]
    print('after an exact-name miss in the same directory (case-insensitive fallback): %d' % len(after_miss))
    by_dir = collections.Counter(s[0] for s in scan_done)
    for d, n in by_dir.most_common(a.top):
        print('%6d  %s' % (n, d))
    print('\nnames whose miss led to a directory scan (top):')
    for name, n in collections.Counter(os.path.basename(s[3]) for s in after_miss).most_common(a.top):
        print('%6d  %s' % (n, name))
    print('\n## most repeated failed lookups')
    for p, n in fail_paths.most_common(a.top):
        print('%6d  %s' % (n, p))
    if files_re:
        times = sorted(first_open.values())
        print('\n## first open of files matching %r: %d files' % (a.files, len(times)))
        for q in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
            if times:
                i = min(len(times) - 1, int(q * (len(times) - 1)))
                print('  %3d%% (%d files) at %.2f s' % (q * 100, i + 1, times[i]))


if __name__ == '__main__':
    sys.exit(main())
