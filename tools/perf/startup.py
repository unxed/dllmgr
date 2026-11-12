#!/usr/bin/env python3
"""Startup timeline of a Wine program on the stand (#87). Measures only.

usage: startup.py --out DIR --prefix PREFIX [options] -- COMMAND...

Starts COMMAND (e.g. `dllmgr run faststone`, `wine Photoshop.exe`) and
records, on CLOCK_MONOTONIC (the clock of Wine's +timestamp lines):
  - X: every top-level window mapped (name, size), screen damage (last
    change), from an observer on $DISPLAY (never use the owner's :0);
  - /proc every 50 ms: each process of the prefix (WINEPREFIX in its
    environment or a descendant of COMMAND): first seen, exit, user+system
    CPU; "quiet" = a --quiet-ms window with less than --quiet-cpu CPU
    seconds summed over all of them;
  - the Wine log (COMMAND's stderr, plus --wine-log files such as the
    trampoline log): +timestamp lines of +loaddll/+process, so set
    WINEDEBUG=+timestamp,+loaddll,+process (cheap) in the environment.
Steps: --step 'REGEX' waits until a window whose name matches is mapped and
the tree is quiet, records it, then runs the step's --do shell command
(empty: next step). After the last step the prefix's wineserver is killed.
Options:
  --cold PATH...  evict PATH's files from the page cache first
                  (posix_fadvise DONTNEED; works without root for files
                  nobody has mapped)
  --strace        run COMMAND under `strace -f -tt -T` (file syscalls) for
                  tools/perf/fs-report.py; times are then inflated
  --server-trace  pre-start `wineserver -f -d1` (request log) for
                  tools/perf/server-report.py; needs --wineserver
  --server-strace pre-start wineserver under `strace -c -f` (syscall mix)
Output in DIR: timeline.txt (ms since launch), summary.json, cpu.tsv,
wine.log (COMMAND's stderr), x.tsv, and the trace files.
"""
import argparse, glob, json, os, re, signal, subprocess, sys, threading, time

T0 = None
HZ = os.sysconf('SC_CLK_TCK')


def now():
    return time.monotonic()


def ms(t):
    return int(round((t - T0) * 1000))


def evict(paths):
    files = size = 0
    for root in paths:
        for top, dirs, names in os.walk(root):
            for name in names:
                path = os.path.join(top, name)
                try:
                    if not os.path.isfile(path) or os.path.islink(path):
                        continue
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                except OSError:
                    continue
                try:
                    os.fsync(fd) if os.access(path, os.W_OK) else None
                    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                    files += 1
                    size += os.fstat(fd).st_size
                except OSError:
                    pass
                finally:
                    os.close(fd)
    return files, size


class Procs(threading.Thread):
    """Polls /proc: processes of the prefix and descendants of the root pid."""

    def __init__(self, prefix, root_pid, period=0.05):
        super().__init__(daemon=True)
        self.prefix, self.root, self.period = prefix, root_pid, period
        self.seen = {}  # pid -> dict(comm, first, last, cpu, start_ticks)
        self.skip = set()
        self.series = []  # (t, total cpu s)
        self.stop = False
        self.lock = threading.Lock()

    def ours(self, pid, ppid):
        if pid in self.seen:
            return True
        if ppid in self.seen or pid == self.root:
            return True
        try:
            with open('/proc/%d/environ' % pid, 'rb') as f:
                env = f.read()
        except OSError:
            return False
        return (b'WINEPREFIX=' + self.prefix.encode() + b'\0') in env

    def poll(self):
        t = now()
        alive = set()
        for name in os.listdir('/proc'):
            if not name.isdigit():
                continue
            pid = int(name)
            if pid in self.skip:
                continue
            try:
                with open('/proc/%d/stat' % pid) as f:
                    stat = f.read()
            except OSError:
                continue
            comm = stat[stat.index('(') + 1:stat.rindex(')')]
            rest = stat[stat.rindex(')') + 2:].split()
            ppid, utime, stime, start = int(rest[1]), int(rest[11]), int(rest[12]), int(rest[19])
            if not self.ours(pid, ppid):
                if pid not in self.seen and t - T0 > 1 and pid < self.root:
                    self.skip.add(pid)  # old unrelated process: never ours later
                continue
            alive.add(pid)
            with self.lock:
                p = self.seen.setdefault(pid, dict(comm=comm, first=t, ppid=ppid, start_ticks=start, user=0, sys=0))
                p.update(comm=comm, last=t, user=utime / HZ, sys=stime / HZ)
                if p.get('exe') is None:
                    try:
                        p['exe'] = os.readlink('/proc/%d/exe' % pid)
                    except OSError:
                        pass
        with self.lock:
            for pid, p in self.seen.items():
                if pid not in alive and 'gone' not in p:
                    p['gone'] = t
            self.series.append((t, sum(p['user'] + p['sys'] for p in self.seen.values() if p['comm'] != 'strace')))

    def run(self):
        while not self.stop:
            self.poll()
            time.sleep(self.period)

    def quiet_since(self, window, limit):
        """Start time of the newest quiet window, or None if busy now."""
        with self.lock:
            s = list(self.series)
        if not s or s[-1][0] - s[0][0] < window:
            return None
        end_t, end_c = s[-1]
        for t, c in reversed(s):
            if end_t - t >= window:
                return t if end_c - c < limit else None
        return None


class XWatch(threading.Thread):
    def __init__(self, out):
        super().__init__(daemon=True)
        from Xlib import display, X
        from Xlib.ext import damage
        self.X, self.damage = X, damage
        self.d = display.Display()
        self.root = self.d.screen().root
        self.root.change_attributes(event_mask=X.SubstructureNotifyMask)
        self.has_damage = self.d.has_extension('DAMAGE')
        if self.has_damage:
            self.d.damage_query_version()
            self.damage_id = self.root.damage_create(damage.DamageReportNonEmpty)
        self.events = []  # (t, kind, wid, name, geometry)
        self.damage_times = []
        self.out = out
        self.lock = threading.Lock()

    def name_of(self, w, depth=0):
        try:
            for atom in ('_NET_WM_NAME', 'WM_NAME'):
                prop = w.get_full_property(self.d.intern_atom(atom), self.X.AnyPropertyType)
                if prop and prop.value:
                    v = prop.value
                    return v.decode('utf-8', 'replace') if isinstance(v, bytes) else str(v)
            if depth < 2:
                for child in w.query_tree().children:
                    n = self.name_of(child, depth + 1)
                    if n:
                        return n
        except Exception:
            pass
        return ''

    def run(self):
        X = self.X
        while True:
            e = self.d.next_event()
            t = now()
            if e.type == X.MapNotify:
                w = e.window
                try:
                    g = w.get_geometry()
                    geo = '%dx%d+%d+%d' % (g.width, g.height, g.x, g.y)
                    over = w.get_attributes().override_redirect
                except Exception:
                    geo, over = '?', 0
                name = self.name_of(w)
                if not name:  # the WM may set the name a moment later
                    time.sleep(0.05)
                    name = self.name_of(w)
                with self.lock:
                    self.events.append((t, 'map' + ('-or' if over else ''), w.id, name, geo))
            elif e.type == X.UnmapNotify:
                with self.lock:
                    self.events.append((t, 'unmap', e.window.id, '', ''))
            elif self.has_damage and e.__class__.__name__ == 'DamageNotify':
                self.damage_times.append(t)
                try:
                    self.d.damage_subtract(self.damage_id)
                except Exception:
                    pass

    def mapped_matching(self, regex, after=0):
        with self.lock:
            for t, kind, wid, name, geo in self.events:
                if kind.startswith('map') and t >= after and re.search(regex, name):
                    return t, wid, name
        return None


WINE_LINE = re.compile(r'^\s*(\d+\.\d{3}):([0-9a-f]{4}):(\w+):(\w+):(\S+)\s*(.*)$')


def wine_events(paths, base):
    """Startup markers from +timestamp Wine logs."""
    ev = []
    loads = 0
    first = None
    last_load = None
    for path in paths:
        try:
            text = open(path, errors='replace').read()
        except OSError:
            continue
        for line in text.splitlines():
            m = WINE_LINE.match(line)
            if not m:
                continue
            t = float(m.group(1))
            if t < base - 5:
                continue  # an older run in an appended log
            if first is None or t < first:
                first = t
            chan, func, rest = m.group(4), m.group(5), m.group(6)
            if chan == 'loaddll' and 'Loaded' in rest:
                loads += 1
                last_load = t
                path_m = re.search(r'Loaded L"([^"]+)"', rest)
                mod = path_m.group(1) if path_m else rest
                kind = rest.rsplit(':', 1)[-1].strip()
                low = mod.lower()
                if low.endswith('.exe') or kind == 'native':
                    ev.append((t, 'load %s (%s) [%s]' % (mod.split('\\')[-1], kind, m.group(2))))
            elif chan == 'process' and func.startswith('NtCreateUserProcess') and ' pid ' in rest:
                ev.append((t, 'process created: ' + rest.split('"')[1].split('\\')[-1] if '"' in rest else rest))
    if first is not None:
        ev.append((first, 'wine: first log line'))
    if last_load is not None:
        ev.append((last_load, 'wine: last DLL load (%d loads)' % loads))
    return ev


def main():
    global T0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--step', action='append', default=[], help='window name regex to wait for')
    ap.add_argument('--do', action='append', default=[], help='shell command after the matching step ($WID)')
    ap.add_argument('--quiet-ms', type=int, default=1000)
    ap.add_argument('--quiet-cpu', type=float, default=0.05)
    ap.add_argument('--timeout', type=float, default=120)
    ap.add_argument('--settle', type=float, default=0, help='extra seconds after the last step')
    ap.add_argument('--cold', nargs='*', default=[])
    ap.add_argument('--wine-log', action='append', default=[], help='more Wine logs (glob, files written during the run)')
    ap.add_argument('--wineserver', default='/opt/wine-stable/bin/wineserver')
    ap.add_argument('--no-wine-trace', dest='wine_trace', action='store_false',
                    help='do not add +timestamp,+loaddll,+process to WINEDEBUG')
    ap.add_argument('--strace', action='store_true')
    ap.add_argument('--server-trace', action='store_true')
    ap.add_argument('--server-strace', action='store_true')
    ap.add_argument('command', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd:
        ap.error('no COMMAND')
    if os.environ.get('DISPLAY', '') in ('', ':0', ':0.0'):
        sys.exit('startup.py: refusing DISPLAY %r (stand displays only)' % os.environ.get('DISPLAY'))
    os.makedirs(a.out, exist_ok=True)
    prefix = os.path.realpath(a.prefix)
    env = dict(os.environ, WINEPREFIX=prefix)
    if a.wine_trace and '+timestamp' not in env.get('WINEDEBUG', ''):
        env['WINEDEBUG'] = ','.join(x for x in (env.get('WINEDEBUG'), '+timestamp,+loaddll,+process') if x)
    notes = ['load average before the run: %.2f %.2f %.2f (other agents share the machine)' % os.getloadavg()]
    subprocess.run([a.wineserver, '-k'], env=env, stderr=subprocess.DEVNULL)
    stale = 0
    keep, pid = set(), os.getpid()
    while pid > 1:  # never our own ancestors
        keep.add(pid)
        try:
            pid = int(open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    for name in os.listdir('/proc'):  # leftovers of an earlier run in this (our own) prefix
        try:
            with open('/proc/%s/environ' % name, 'rb') as f:
                if name.isdigit() and int(name) not in keep and (b'WINEPREFIX=' + prefix.encode() + b'\0') in f.read():
                    os.kill(int(name), signal.SIGKILL)
                    stale += 1
        except OSError:
            pass
    if stale:
        notes.append('killed %d leftover processes of this prefix' % stale)
    time.sleep(0.5)
    if a.cold:
        files, size = evict(a.cold)
        notes.append('cold: evicted %d files, %.0f MB' % (files, size / 1e6))
    server = None
    if a.server_trace or a.server_strace:
        scmd = [a.wineserver, '-f', '-p5'] + (['-d1'] if a.server_trace else [])
        if a.server_strace:
            scmd = ['strace', '-c', '-f', '-o', os.path.join(a.out, 'wineserver-strace.txt')] + scmd
        server = subprocess.Popen(scmd, env=env, stdout=subprocess.DEVNULL,
                                  stderr=open(os.path.join(a.out, 'server.log'), 'wb'))
        time.sleep(1.0)
    if a.strace:
        if a.quiet_cpu == 0.05:
            a.quiet_cpu = 0.25  # traced idle polling is inflated too
        cmd = ['strace', '-f', '-tt', '-T', '-qq', '-s', '300', '-o', os.path.join(a.out, 'fs.strace'),
               '-e', 'trace=%file,getdents64,clone,clone3,vfork,fork,prctl,ioctl,close,execve'] + cmd
    x = XWatch(a.out)
    x.start()
    log = open(os.path.join(a.out, 'wine.log'), 'wb')
    T0 = now()
    proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    procs = Procs(prefix, proc.pid)
    procs.start()
    marks = [(T0, 'launch: ' + ' '.join(cmd)[-160:])]
    steps = a.step or []
    deadline = T0 + a.timeout
    after = T0
    timed_out = False
    for i, regex in enumerate(steps):
        hit = None
        while now() < deadline:
            hit = hit or x.mapped_matching(regex, after)
            if hit:
                q = procs.quiet_since(a.quiet_ms / 1000.0, a.quiet_cpu)
                if q is not None and q >= hit[0] - 0.001:
                    break
                if q is not None and now() - hit[0] > a.quiet_ms / 1000.0:
                    break
            time.sleep(0.05)
        else:
            timed_out = True
            marks.append((now(), 'TIMEOUT waiting for step %d %r' % (i + 1, regex)))
            break
        marks.append((hit[0], 'step %d mapped: %s' % (i + 1, hit[2])))
        q = procs.quiet_since(a.quiet_ms / 1000.0, a.quiet_cpu)
        marks.append((q if q is not None else now(), 'step %d quiet (CPU < %.2f s per %d ms)' % (i + 1, a.quiet_cpu, a.quiet_ms)))
        if i < len(a.do) and a.do[i]:
            marks.append((now(), 'step %d action: %s' % (i + 1, a.do[i])))
            subprocess.run(a.do[i], shell=True, env=dict(env, WID=str(hit[1])))
            after = now()
    if not steps:
        while now() < deadline and proc.poll() is None:
            time.sleep(0.1)
    time.sleep(a.settle)
    end = now()
    marks.append((end, 'end of measurement'))
    # stop the app: every wineserver binary seen for our prefix (stock and
    # private runtime), then whatever of ours is left (the trampoline's
    # dllmgr runs in its own session), checked by WINEPREFIX against pid reuse
    with procs.lock:
        servers = {p.get('exe') for p in procs.seen.values() if 'wineserver' in p['comm'] and p.get('exe')}
        ours = list(procs.seen)
    for srv in sorted(servers | {a.wineserver}):
        subprocess.run([srv, '-k'], env=env, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
    for pid in ours:
        try:
            with open('/proc/%d/environ' % pid, 'rb') as f:
                mine = (b'WINEPREFIX=' + prefix.encode() + b'\0') in f.read()
            if mine:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    if server:
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    procs.stop = True
    time.sleep(0.1)
    log.close()
    # events
    ev = list(marks)
    with procs.lock:
        for pid, p in sorted(procs.seen.items(), key=lambda kv: kv[1]['first']):
            ev.append((p['first'], 'proc %d %s seen' % (pid, p['comm'])))
    with x.lock:
        for t, kind, wid, name, geo in x.events:
            if kind.startswith('map'):
                ev.append((t, 'X %s 0x%x %s %r' % (kind, wid, geo, name)))
    logs = [os.path.join(a.out, 'wine.log')]
    for pattern in a.wine_log:  # e.g. PREFIX/.dllmgr/runs/*.log (dllmgr run keeps +loaddll out of stderr)
        logs += [p for p in glob.glob(pattern) if os.path.getmtime(p) >= time.time() - (now() - T0) - 1]
    ev += wine_events(logs, T0)
    shown = [t for t in x.damage_times if t <= end]
    last_damage = shown[-1] if shown else None
    if last_damage:
        ev.append((last_damage, 'X last screen change before the end (%d damage events)' % len(shown)))
    ev.sort(key=lambda e: e[0])
    with open(os.path.join(a.out, 'timeline.txt'), 'w') as f:
        for n in notes:
            f.write('# ' + n + '\n')
        for t, what in ev:
            f.write('%7d ms  %s\n' % (ms(t), what))
    with open(os.path.join(a.out, 'x.tsv'), 'w') as f:
        for t, kind, wid, name, geo in x.events:
            f.write('%d\t%s\t0x%x\t%s\t%s\n' % (ms(t), kind, wid, geo, name))
    with open(os.path.join(a.out, 'cpu.tsv'), 'w') as f:
        for t, c in procs.series:
            f.write('%d\t%.2f\n' % (ms(t), c))
    groups = {}
    for pid, p in procs.seen.items():
        comm = p['comm']
        key = ('wineserver' if 'wineserver' in comm else
               'python (dllmgr)' if comm.startswith('python') else comm)
        g = groups.setdefault(key, dict(n=0, user=0.0, sys=0.0))
        g['n'] += 1
        g['user'] += p['user']
        g['sys'] += p['sys']
    summary = dict(command=cmd, prefix=prefix, notes=notes, timed_out=timed_out,
                   end_ms=ms(end), steps=[(ms(t), w) for t, w in marks],
                   cpu=groups, cpu_total=round(sum(g['user'] + g['sys'] for g in groups.values()), 2),
                   last_damage_ms=ms(last_damage) if last_damage else None)
    json.dump(summary, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(open(os.path.join(a.out, 'timeline.txt')).read()[-6000:])
    print('CPU seconds (user/sys) per process name:')
    for k, g in sorted(groups.items(), key=lambda kv: -(kv[1]['user'] + kv[1]['sys'])):
        print('  %-28s x%-2d %6.2f / %6.2f' % (k, g['n'], g['user'], g['sys']))
    return 1 if timed_out else 0


if __name__ == '__main__':
    sys.exit(main())
