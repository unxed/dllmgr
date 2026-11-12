#!/usr/bin/env python3
"""Catch the failing call behind an error in a Wine program (#89).

  fault.py run --out DIR --prefix PFX [--runtime RT] [options] -- COMMAND...
  fault.py report DIR [--good GOODDIR]
  fault.py diff GOODDIR BADDIR

`run` starts COMMAND with cheap targeted Wine logging (+timestamp,+pid,+seh,
+loaddll and +relay limited by RelayInclude to lookups and UI text calls of
Wine's own builtin DLLs), watches for the failure moment (an error text in a
dialog/MessageBox, an unhandled exception, a non-zero exit, a hung window
that no longer answers _NET_WM_PING), takes a screenshot and a winedbg
`bt all` at that moment, stops the program and prints the report.

`report` reads DIR/wine.log (+ DIR/meta.json) and prints one screen:
trigger, the exception behind it (module+offset, SEH handler chain, C++
rethrows), the calls the faulting module made just before it, the ranked
failing calls (time and thread nearness, rarity in the run, noise list
tools/fault/noise.txt, and with --good: failed there too / worked there),
not-found lookups, rare err:/fixme: lines, and where to look next.

`diff` compares a good and a bad run of the same program: first bad-only
events, calls whose result flipped, lookups only the good run made,
exceptions only the bad run had.

The interface follows tools/perf/startup.py. Stand displays only: refuses
DISPLAY :0. See tools/fault/README.md.
"""
import argparse
import collections
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- presets
LOOKUPS = ('CreateFileA CreateFileW GetFileAttributesA GetFileAttributesW GetFileAttributesExA '
           'GetFileAttributesExW FindFirstFileA FindFirstFileW FindFirstFileExA FindFirstFileExW '
           'LoadLibraryA LoadLibraryW LoadLibraryExA LoadLibraryExW GetProcAddress '
           'RegOpenKeyA RegOpenKeyW RegOpenKeyExA RegOpenKeyExW RegCreateKeyExA RegCreateKeyExW '
           'RegQueryValueA RegQueryValueW RegQueryValueExA RegQueryValueExW RegGetValueA RegGetValueW '
           'RegEnumKeyA RegEnumKeyW RegEnumKeyExA RegEnumKeyExW RegEnumValueA RegEnumValueW '
           'RegSetValueExA RegSetValueExW RegDeleteKeyA RegDeleteKeyW RegDeleteValueA RegDeleteValueW '
           'CoCreateInstance CoGetClassObject CLSIDFromProgID AddFontResourceExA AddFontResourceExW '
           'RaiseException').split()
UI = ('MessageBoxA MessageBoxW MessageBoxExA MessageBoxExW MessageBoxIndirectA MessageBoxIndirectW '
      'DialogBoxParamA DialogBoxParamW DialogBoxIndirectParamA DialogBoxIndirectParamW '
      'SetWindowTextA SetWindowTextW SetDlgItemTextA SetDlgItemTextW DrawTextA DrawTextW '
      'DrawTextExA DrawTextExW').split()
PRESETS = {'lookups': LOOKUPS + UI, 'ui': UI, 'none': []}
TEXT_FUNCS = re.compile(r'^(MessageBox\w*|SetWindowText[AW]|SetDlgItemText[AW]|DrawText(Ex)?[AW])$')
DEFAULT_TRIGGER = r'(?i)program error|unexpected error|fatal error|has stopped working|runtime error'

# result rules for relayed calls: kind of return value that means failure
RULES = [
    (re.compile(r'^Reg[A-Z]\w*$'), 'win32err'),
    (re.compile(r'^(CreateFile\w*|FindFirstFile\w*)$'), 'handle'),
    (re.compile(r'^GetFileAttributes[AW]$'), 'minus1'),
    (re.compile(r'^(GetFileAttributesEx[AW]|LoadLibrary\w*|GetProcAddress|GetModuleHandle\w*|'
                r'FindResource\w*|LoadResource|AddFontResource\w*)$'), 'zero'),
    (re.compile(r'^(Nt|Zw|Ldr)[A-Z]\w*$'), 'ntstatus'),
    (re.compile(r'^(Co[A-Z]\w*|CLSIDFromProgID|Ole[A-Z]\w*|SH[A-Z]\w*)$'), 'hresult'),
]
WIN32ERR = {2: 'NOT FOUND', 3: 'PATH NOT FOUND', 5: 'ACCESS DENIED', 6: 'INVALID HANDLE',
            0x57: 'INVALID PARAMETER', 0x7e: 'MODULE NOT FOUND', 0x7f: 'PROC NOT FOUND',
            0xa1: 'BAD PATHNAME', 0x3f2: 'BADKEY', 0x3f9: 'NOT REGISTRY FILE'}
NOT_FAIL_WIN32 = {0, 0xea, 0x103}  # ok, MORE_DATA (size query), NO_MORE_ITEMS (end of enumeration)
EXC_NAMES = {0xc0000005: 'ACCESS_VIOLATION', 0xc0000094: 'INT_DIVIDE_BY_ZERO', 0xc0000095: 'INT_OVERFLOW',
             0xc000008e: 'FLT_DIVIDE_BY_ZERO', 0xc0000090: 'FLT_INVALID_OPERATION', 0xc00000fd: 'STACK_OVERFLOW',
             0xc000001d: 'ILLEGAL_INSTRUCTION', 0xc0000096: 'PRIV_INSTRUCTION', 0xc0000409: 'STACK_BUFFER_OVERRUN',
             0x80000003: 'BREAKPOINT', 0xe06d7363: 'C++ exception', 0x406d1388: 'thread name',
             0x80000026: 'LONGJUMP', 0xc0000025: 'NONCONTINUABLE', 0x40010006: 'OutputDebugString'}
BENIGN_EXC = {0x406d1388, 0x80000026, 0x40010006, 0x4001000a, 0x80000003}
ROOT = {'80000000': 'HKCR', '80000001': 'HKCU', '80000002': 'HKLM', '80000003': 'HKU', '80000005': 'HKCC'}


# ---------------------------------------------------------------- parsing
PREFIX = re.compile(r'^(?:(\d+\.\d+):)?(?:([0-9a-f]{4,8}):)?([0-9a-f]{4,8}):(.*)$')
CALL = re.compile(r'^Call ([\w.]+?)\.(\w+)\((.*)\) ret=([0-9a-f]+)$')
RET = re.compile(r'^Ret  ([\w.]+?)\.(\w+)\(\) retval=([0-9a-f]+) ret=([0-9a-f]+)$')
CHAN = re.compile(r'^(err|fixme|warn|trace):(\w+):(\S+) ?(.*)$')
STR = re.compile(r'L?"((?:[^"\\]|\\.)*)"')
LOADED = re.compile(r'Loaded L"(.*)" at ([0-9A-Fa-f]+): (\w+)')
UNLOADED = re.compile(r'Unloaded module L"(.*)" : (\w+)')
DISPATCH = re.compile(r'dispatch_exception code=([0-9a-f]+)(?: \((\w+)\))? flags=([0-9a-f]+) addr=([0-9A-Fa-f]+)')
HANDLER = re.compile(r'call_seh_handlers calling handler at ([0-9A-Fa-f]+)')
RETHROW = re.compile(r'detect rethrow: exception code: ([0-9a-f]+)')
CATCH = re.compile(r'call_catch_block calling handler ([0-9A-Fa-f]+)')
UNHANDLED = re.compile(r'wine: Unhandled (.*?) at address ([0-9A-Fa-f]+)(?: \(thread ([0-9a-f]+)\))?')


def unescape(s):
    return s.replace('\\\\', '\\').replace('\\"', '"')


class Module:
    __slots__ = ('name', 'path', 'base', 'kind', 't0', 't1')

    def __init__(self, path, base, kind, t0):
        self.path, self.base, self.kind, self.t0, self.t1 = path, base, kind, t0, None
        self.name = path.replace('\\\\', '\\').split('\\')[-1]


class Run:
    """Everything the report needs from one wine.log."""

    def __init__(self, path, meta=None):
        self.path = path
        self.meta = meta or {}
        self.modules = collections.defaultdict(list)  # pid -> [Module]
        self.calls = []        # dicts: t pid tid dll func args strs caller retval fail res
        self.exceptions = []   # dicts: t pid tid code addr handlers catch rethrow_of n
        self.chan = []         # (t, pid, tid, level, channel, func, msg)
        self.unhandled = []    # (t, pid, tid, what, addr)
        self.exe = {}          # pid -> main exe name
        self.first_t = self.last_t = None
        self.lines = 0
        self.parse()

    def parse(self):
        pending = collections.defaultdict(list)
        cur_exc = {}
        last_t = 0.0
        with open(self.path, 'rb') as f:
            for raw in f:
                self.lines += 1
                line = raw.decode('utf-8', 'replace').rstrip('\n')
                m = PREFIX.match(line)
                if not m:
                    u = UNHANDLED.search(line)
                    if u:
                        self.unhandled.append((last_t, None, u.group(3), u.group(1), int(u.group(2), 16)))
                    continue
                t = float(m.group(1)) if m.group(1) else last_t
                last_t = t
                pid, tid, rest = m.group(2) or '0', m.group(3), m.group(4)
                if self.first_t is None:
                    self.first_t = t
                self.last_t = t
                if rest.startswith('Call '):
                    c = CALL.match(rest)
                    if c:
                        args = c.group(3)
                        rec = dict(t=t, pid=pid, tid=tid, dll=c.group(1), func=c.group(2), args=args,
                                   strs=[unescape(s) for s in STR.findall(args)], caller=int(c.group(4), 16),
                                   retval=None)
                        pending[(pid, tid)].append(rec)
                        self.calls.append(rec)
                    continue
                if rest.startswith('Ret  '):
                    r = RET.match(rest)
                    if r:
                        stack = pending[(pid, tid)]
                        for i in range(len(stack) - 1, -1, -1):
                            if stack[i]['func'] == r.group(2):
                                rec = stack.pop(i)
                                del stack[i:]
                                rec['retval'] = int(r.group(3), 16)
                                rec['t_ret'] = t
                                break
                    continue
                c = CHAN.match(rest)
                if not c:
                    u = UNHANDLED.search(rest)
                    if u:
                        self.unhandled.append((t, pid, u.group(3) or tid, u.group(1), int(u.group(2), 16)))
                    continue
                level, chan, func, msg = c.groups()
                if chan == 'loaddll':
                    lm = LOADED.search(msg)
                    if lm:
                        mod = Module(lm.group(1), int(lm.group(2), 16), lm.group(3), t)
                        self.modules[pid].append(mod)
                        if mod.name.lower().endswith('.exe') and pid not in self.exe:
                            self.exe[pid] = mod.name
                        continue
                    um = UNLOADED.search(msg)
                    if um:
                        for mod in reversed(self.modules[pid]):
                            if mod.path == um.group(1) and mod.t1 is None:
                                mod.t1 = t
                                break
                    continue
                if chan == 'seh':
                    d = DISPATCH.search(msg)
                    if d:
                        code, addr = int(d.group(1), 16), int(d.group(4), 16)
                        prev = cur_exc.get((pid, tid))
                        if prev and prev['code'] == code and prev['addr'] == addr and t - prev['t'] < 0.05 \
                                and not prev['handlers']:
                            cur_exc[(pid, tid)] = prev  # the 32-bit half of a new-WoW64 dispatch
                            continue
                        e = dict(t=t, pid=pid, tid=tid, code=code, addr=addr, handlers=[], catch=None,
                                 rethrow_of=None, first=int(d.group(3), 16) == 0 or code != 0xe06d7363)
                        self.exceptions.append(e)
                        cur_exc[(pid, tid)] = e
                        continue
                    e = cur_exc.get((pid, tid))
                    if e is None:
                        continue
                    h = HANDLER.search(msg)
                    if h:
                        e['handlers'].append(int(h.group(1), 16))
                        continue
                    r = RETHROW.search(msg)
                    if r and e['code'] == 0xe06d7363:
                        e['rethrow_of'] = int(r.group(1), 16)
                        continue
                    k = CATCH.search(msg)
                    if k and e['catch'] is None:
                        e['catch'] = int(k.group(1), 16)
                    continue
                if level in ('err', 'fixme'):
                    self.chan.append((t, pid, tid, level, chan, func, msg))
                u = UNHANDLED.search(rest)
                if u:
                    self.unhandled.append((t, pid, u.group(3) or tid, u.group(1), int(u.group(2), 16)))
        for rec in self.calls:
            rec['fail'], rec['res'] = classify(rec)
        # how often each signature / exception site occurs in this run
        self.sig_count = collections.Counter(sig(self, c) for c in self.calls)
        self.exc_count = collections.Counter((e['code'], self.where(e['pid'], e['t'], e['addr'], short=True))
                                             for e in self.exceptions)

    def module_at(self, pid, t, addr):
        best = None
        for mod in self.modules.get(pid, ()):
            if mod.base <= addr and mod.t0 <= t + 0.001 and (mod.t1 is None or mod.t1 >= t):
                if best is None or mod.base > best.base:
                    best = mod
        if best is None or addr - best.base > 0x4000000:
            return None
        return best

    def where(self, pid, t, addr, short=False):
        mod = self.module_at(pid, t, addr)
        if mod is None:
            return '%08x' % addr
        name = norm_name(mod.name) if short else mod.name
        return '%s+0x%x' % (name, addr - mod.base)


def classify(rec):
    """(failed?, short result text) of a relayed call."""
    rv = rec['retval']
    if rv is None:
        return False, 'no return'
    for rx, kind in RULES:
        if rx.match(rec['func']):
            break
    else:
        return False, '%x' % rv
    if kind == 'win32err':
        if rv in NOT_FAIL_WIN32:
            return False, {0: 'ok', 0xea: 'more data', 0x103: 'end'}[rv]
        return True, '%d %s' % (rv, WIN32ERR.get(rv, 'error'))
    if kind == 'handle':
        return (True, 'FAILED (-1)') if rv in (0xffffffff, 0xffffffffffffffff) else (False, 'ok')
    if kind == 'minus1':
        return (True, 'FAILED (not found)') if rv in (0xffffffff, 0xffffffffffffffff) else (False, 'ok')
    if kind == 'zero':
        return (True, 'NULL/FALSE') if rv == 0 else (False, 'ok')
    if kind == 'ntstatus':
        return (rv & 0x80000000 != 0 and rv & 0xc0000000 == 0xc0000000), '%08x' % rv
    if kind == 'hresult':
        return (rv & 0x80000000 != 0), ('ok' if rv == 0 else '%08x' % rv)
    return False, '%x' % rv


def norm_str(s):
    s = s.lower()
    s = re.sub(r'~[0-9a-z]+\.tmp', '~*.tmp', s)
    s = re.sub(r'\.\d{4}\.dir\.\d{4}', '.#.dir.#', s)
    return s


def norm_name(name):
    return norm_str(name)


def call_text(run, c, width=110):
    args = c['args']
    strs = c['strs']
    first = args.split(',', 1)[0]
    root = ROOT.get(first.lower()) if c['func'].startswith('Reg') else None
    shown = ', '.join('"%s"' % s for s in strs) if strs else args
    if root:
        shown = root + ', ' + shown
    elif c['func'].startswith('Reg') and strs:
        shown = 'h%s, %s' % (first.lstrip('0') or '0', shown)
    if c['func'].startswith('RegEnum'):
        parts = args.split(',')
        shown = 'h%s, #%d' % (first.lstrip('0') or '0', int(parts[1], 16) if len(parts) > 1 else -1)
    text = '%s(%s)' % (c['func'], shown)
    return text if len(text) <= width else text[:width - 3] + '...'


def sig(run, c):
    """Call signature without pointers/handles/time: for rarity and diff."""
    caller = run.module_at(c['pid'], c['t'], c['caller'])
    mod = norm_name(caller.name) if caller else '?'
    first = c['args'].split(',', 1)[0].lower()
    root = ROOT.get(first, '') if c['func'].startswith('Reg') else ''
    extra = ''
    if c['func'].startswith('RegEnum'):
        parts = c['args'].split(',')
        extra = '#%s' % (int(parts[1], 16) if len(parts) > 1 else '?')
    return (mod, c['func'].rstrip('AW') if c['func'][-1:] in 'AW' else c['func'], root,
            tuple(norm_str(s) for s in c['strs']), extra)


# ---------------------------------------------------------------- noise
def load_noise(path=None):
    path = path or os.path.join(HERE, 'noise.txt')
    rules = []
    try:
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if line and not line.startswith('#'):
                rules.append(re.compile(line, re.I))
    except OSError:
        pass
    return rules


def noisy(rules, text):
    return any(r.search(text) for r in rules)


# ---------------------------------------------------------------- trigger
def find_trigger(run, trigger_re):
    """The failure moment: dict(kind, t, pid, tid, text)."""
    rx = re.compile(trigger_re) if trigger_re else None
    cands = []
    for c in run.calls:
        if not TEXT_FUNCS.match(c['func']):
            continue
        text = ' | '.join(c['strs'])
        hit = rx is not None and rx.search(text)
        if not hit and c['func'].startswith('MessageBox') and not c['func'].startswith('MessageBoxIndirect'):
            parts = c['args'].split(',')
            try:
                hit = len(parts) >= 4 and int(parts[-1].strip()[:8], 16) & 0x10  # MB_ICONHAND
            except ValueError:
                hit = False
        if hit:
            cands.append(dict(kind='dialog', t=c['t'], pid=c['pid'], tid=c['tid'],
                              text='%s.%s "%s"' % (c['dll'], c['func'], text[:100])))
            break
    for t, pid, tid, what, addr in run.unhandled:
        cands.append(dict(kind='unhandled', t=t, pid=pid, tid=tid,
                          text='Unhandled %s at %s' % (what, run.where(pid, t, addr) if pid else '%08x' % addr)))
        break
    tx = run.meta.get('trigger') or {}
    if tx.get('kind') == 'hang':
        pid = main_pid(run)
        cands.append(dict(kind='hang', t=tx['t_wine'], pid=pid, tid=first_tid(run, pid), text=tx.get('text', 'hang')))
    if cands:
        return min(cands, key=lambda c: c['t'])
    code = run.meta.get('exit_code')
    if code not in (None, 0) and not run.meta.get('stopped_by_us'):
        pid = main_pid(run)
        return dict(kind='exit', t=run.last_t, pid=pid, tid=first_tid(run, pid),
                    text='exit code %d (0x%x)' % (code, code & 0xffffffff))
    # no trigger: the last rare non-C++ exception, if any
    for e in reversed(run.exceptions):
        if e['code'] not in BENIGN_EXC and e['code'] != 0xe06d7363 and \
                run.exc_count[(e['code'], run.where(e['pid'], e['t'], e['addr'], short=True))] <= 3:
            return dict(kind='exception', t=e['t'], pid=e['pid'], tid=e['tid'],
                        text='no trigger matched; last rare exception %08x' % e['code'])
    return None


def main_pid(run):
    if run.exe:
        counts = collections.Counter(c['pid'] for c in run.calls)
        return max(run.exe, key=lambda p: counts.get(p, 0))
    return '0'


def first_tid(run, pid):
    for c in run.calls:
        if c['pid'] == pid:
            return c['tid']
    return '?'


def exc_name(code):
    return EXC_NAMES.get(code, '')


def root_exception(run, trig, window):
    """The exception behind the trigger: latest rare first-chance exception of
    the trigger thread before it (C++ rethrows lead back to their origin)."""
    cands = [e for e in run.exceptions
             if e['pid'] == trig['pid'] and e['tid'] == trig['tid'] and trig['t'] - window <= e['t'] <= trig['t']
             and e['code'] not in BENIGN_EXC]
    if not cands:
        return None, []
    rethrows = [e for e in cands if e['rethrow_of']]
    for e in reversed(cands):
        if e['code'] == 0xe06d7363:
            continue
        key = (e['code'], run.where(e['pid'], e['t'], e['addr'], short=True))
        if run.exc_count[key] <= 3 or (rethrows and any(r['rethrow_of'] == e['code'] and r['t'] >= e['t']
                                                         for r in rethrows)):
            return e, [r for r in rethrows if r['t'] >= e['t'] and r['rethrow_of'] == e['code']]
    return cands[-1], []


# ---------------------------------------------------------------- report
def report(run, trigger_re=DEFAULT_TRIGGER, good=None, window=30.0, top=10, noise=None, out=sys.stdout):
    noise = load_noise() if noise is None else noise
    w = out.write
    t0 = run.meta.get('t0_wine') or run.first_t or 0.0
    w('== fault report: %s\n' % os.path.dirname(os.path.abspath(run.path)))
    if run.meta.get('command'):
        w('command: %s\n' % ' '.join(run.meta['command'])[-150:])
    w('log: %d lines, %d relayed calls, %d exceptions, %.1f s\n' % (
        run.lines, len(run.calls), len(run.exceptions), (run.last_t or 0) - (run.first_t or 0)))
    trig = find_trigger(run, trigger_re)
    if trig is None:
        w('TRIGGER: none found (no matching dialog text, no unhandled exception, exit 0, no hang)\n')
        return None
    pid, tid, tt = trig['pid'], trig['tid'], trig['t']
    w('\nTRIGGER  %s at %.2f s: %s\n         process %s (%s), thread %s\n' % (
        trig['kind'], tt - t0, trig['text'], pid, run.exe.get(pid, '?'), tid))
    exc, rethrows = root_exception(run, trig, window)
    fault_mod = None
    if exc:
        where = run.where(exc['pid'], exc['t'], exc['addr'])
        mod = run.module_at(exc['pid'], exc['t'], exc['addr'])
        fault_mod = mod
        n = run.exc_count[(exc['code'], run.where(exc['pid'], exc['t'], exc['addr'], short=True))]
        w('\nEXCEPTION behind it (thread %s, %.3f s before): %08x %s at %s  (x%d in run)\n' % (
            exc['tid'], tt - exc['t'], exc['code'], exc_name(exc['code']), where, n))
        if mod:
            w('  module: %s (%s)\n' % (mod.path.replace('\\\\', '\\'), mod.kind))
        chain = [run.where(exc['pid'], exc['t'], h) for h in exc['handlers']]
        if chain:
            w('  SEH handler chain (innermost first, a frame list): %s\n' % ' > '.join(dedup(chain)[:10]))
        if exc['catch']:
            w('  caught at %s\n' % run.where(exc['pid'], exc['t'], exc['catch']))
        if rethrows:
            w('  then rethrown %dx as C++ exceptions, caught at: %s\n' % (len(rethrows), ', '.join(
                dedup(run.where(r['pid'], r['t'], r['catch']) for r in rethrows if r['catch']))[:4]))
        before = [c for c in run.calls if c['pid'] == exc['pid'] and c['tid'] == exc['tid'] and c['t'] <= exc['t']
                  and mod is not None and run.module_at(c['pid'], c['t'], c['caller']) is mod][-12:]
        if before:
            w('  last calls of %s before the fault:\n' % mod.name)
            for c in before:
                w('    -%.3fs %-88s -> %s\n' % (exc['t'] - c['t'], call_text(run, c, 88), c['res']))
    others = collections.Counter()
    for e in run.exceptions:
        if e is exc or e['code'] in BENIGN_EXC or e['code'] == 0xe06d7363 or not (tt - window <= e['t'] <= tt + 2):
            continue
        key = (e['code'], run.where(e['pid'], e['t'], e['addr'], short=True))
        if run.exc_count[key] <= 3:
            others[(e['tid'],) + key] += 1
    if others:
        w('  other rare exceptions near it: %s\n' % '; '.join(
            '%08x at %s [thread %s]' % (k[1], k[2], k[0]) for k in list(others)[:5]))
    # ranked failing calls
    gsig = {}
    if good is not None:
        for c in good.calls:
            s = sig(good, c)
            gsig[s] = gsig.get(s, False) or not c['fail']  # True = worked at least once in the good run
            gsig.setdefault(('failed',) + s, False)
            if c['fail']:
                gsig[('failed',) + s] = True
    scored = []
    for c in run.calls:
        if not c['fail'] or c['pid'] != pid or not (tt - window <= c['t'] <= tt):
            continue
        s = sig(run, c)
        dt = tt - c['t']
        score = 1.0 / (1.0 + dt / 2.0)
        score *= 2.0 if c['tid'] == tid else 1.0
        score /= math.sqrt(run.sig_count[s])
        caller = run.module_at(c['pid'], c['t'], c['caller'])
        if fault_mod is not None and caller is fault_mod:
            score *= 1.5
        tag = ''
        text = call_text(run, c)
        if noisy(noise, '%s %s' % (text, caller.name if caller else '')):
            score *= 0.1
            tag = 'noise'
        if good is not None:
            if gsig.get(('failed',) + s):
                score *= 0.2
                tag = 'fails in good run too'
            elif gsig.get(s):
                score *= 1.5
                tag = 'WORKS in good run'
            else:
                tag = tag or 'not in good run'
        scored.append((score, c, caller, tag))
    best = {}
    for item in sorted(scored, key=lambda x: -x[0]):
        key = sig(run, item[1])
        if key not in best:
            best[key] = item
    ranked = sorted(best.values(), key=lambda x: -x[0])[:top]
    if ranked:
        w('\nFAILING CALLS before the trigger (ranked: time/thread nearness, rarity%s, noise list):\n' % (
            ', good run' if good is not None else ''))
        for score, c, caller, tag in ranked:
            w('  %5.2f -%6.2fs %s %-70s -> %s  from %s x%d%s\n' % (
                score, tt - c['t'], '*' if c['tid'] == tid else ' ', call_text(run, c, 70), c['res'],
                run.where(c['pid'], c['t'], c['caller']), run.sig_count[sig(run, c)],
                '  [%s]' % tag if tag else ''))
        w('  (* = trigger thread)\n')
    # not found lookups, distinct, newest last
    nf = collections.OrderedDict()
    for c in run.calls:
        if c['fail'] and c['pid'] == pid and tt - window <= c['t'] <= tt and c['strs']:
            kind = ('dll' if c['func'].startswith('LoadLibrary') else 'export' if c['func'] == 'GetProcAddress'
                    else 'reg' if c['func'].startswith('Reg') else 'file')
            key = (kind, c['strs'][-1] if kind == 'export' else c['strs'][0])
            if not noisy(noise, '%s %s' % (kind, key[1])):
                nf.pop(key, None)
                nf[key] = c['t']
    if nf:
        w('\nNOT FOUND in the last %.0f s (distinct, newest last, noise filtered):\n' % window)
        for (kind, name), t in list(nf.items())[-top:]:
            w('  -%6.2fs %-6s %s\n' % (tt - t, kind, name[:110]))
    lines = collections.OrderedDict()
    counts = collections.Counter('%s:%s:%s' % (x[3], x[4], x[5]) for x in run.chan)
    for t, p, th, level, chan, func, msg in run.chan:
        if p == pid and tt - window <= t <= tt + 1:
            key = '%s:%s:%s' % (level, chan, func)
            text = '%s %s' % (key, msg)
            if counts[key] <= 5 and not noisy(noise, text):
                lines.pop(key, None)
                lines[key] = (t, text)
    if lines:
        w('\nRARE err:/fixme: lines near it (newest last):\n')
        for key, (t, text) in list(lines.items())[-8:]:
            w('  %+7.2fs %s\n' % (t - tt, text[:130]))
    bt = os.path.join(os.path.dirname(run.path), 'bt.txt')
    if os.path.exists(bt):
        frames = bt_frames(bt, tid)
        if frames:
            w('\nSTACK of thread %s at the trigger (winedbg, bt.txt):\n' % tid)
            for f in frames[:12]:
                w('  %s\n' % f)
    w('\nNEXT:\n')
    for hint in hints(run, trig, exc, fault_mod, ranked, good):
        w('  - %s\n' % hint)
    return trig


def dedup(items):
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def bt_frames(path, tid):
    """Frames of thread TID from winedbg `bt all` output."""
    frames, on = [], False
    want = int(tid, 16) if tid and tid != '?' else None
    for line in open(path, errors='replace'):
        m = re.match(r'Backtrace for thread ([0-9a-fx]+)', line.strip())
        if m:
            on = want is None or int(m.group(1), 16) == want
            continue
        if on and re.match(r'\s*[=>]?\s*\d+ 0x', line):
            frames.append(re.sub(r'\s+', ' ', line.strip()))
    return frames


def hints(run, trig, exc, mod, ranked, good):
    out = []
    if exc and mod:
        if mod.kind == 'native':
            out.append('the fault is inside a native module (%s): it is program code; its input is what it '
                       'read just before (calls above). Compare those values with a good run.' % mod.name)
        else:
            out.append('the fault is inside Wine\'s %s: a Wine bug candidate; rerun with +%s and read '
                       'fix-it-in-wine SKILL.md.' % (mod.name, mod.name.split('.')[0].lower()))
    elif exc:
        out.append('fault address outside any loaded module: freed/unloaded code or a jump through a bad pointer.')
    if any(c['func'] == 'GetProcAddress' and tag != 'noise' for _, c, _, tag in ranked):
        out.append('a missing export: grep Wine\'s .spec for it; stubs show as fixme: lines.')
    if good is None:
        out.append('no good run given: run the same in a prefix/host where it works and use '
                   '`fault.py diff GOOD BAD` (or `report BAD --good GOOD`).')
    if trig['kind'] == 'hang':
        out.append('hang: see bt.txt for every thread; a thread waiting in a critical section names its owner '
                   'in err:sync lines.')
    out.append('raw data: wine.log (grep the thread id), exceptions with +seh, calls with "Call/Ret".')
    return out


# ---------------------------------------------------------------- diff
def events(run):
    """Normalized, time-ordered events for the diff."""
    ev = []
    for c in run.calls:
        if TEXT_FUNCS.match(c['func']) or c['func'] == 'RaiseException':
            continue
        s = sig(run, c)
        ev.append((c['t'], 'call', s, c['res'] if c['fail'] else 'ok', c))
    for e in run.exceptions:
        if e['code'] in BENIGN_EXC:
            continue
        where = run.where(e['pid'], e['t'], e['addr'], short=True)
        if e['code'] == 0xe06d7363:
            continue
        ev.append((e['t'], 'exc', ('%08x' % e['code'], where), '', e))
    for t, pid, tid, level, chan, func, msg in run.chan:
        ev.append((t, level, (chan, func, re.sub(r'[0-9a-fA-F]{6,}|\d+', '#', msg)[:120]), '', None))
    for pid, mods in run.modules.items():
        for m in mods:
            ev.append((m.t0, 'load', (norm_name(m.name), m.kind), '', None))
    ev.sort(key=lambda e: e[0])
    return ev


def show_event(run, e, t0):
    t, kind, s, res, obj = e
    if kind == 'call':
        c = obj
        return '%8.2fs %-60s -> %-14s from %s' % (t - t0, call_text(run, c, 60), c['res'],
                                                 run.where(c['pid'], c['t'], c['caller']))
    if kind == 'exc':
        return '%8.2fs EXCEPTION %s %s at %s' % (t - t0, s[0], exc_name(int(s[0], 16)), s[1])
    if kind == 'load':
        return '%8.2fs load %s (%s)' % (t - t0, s[0], s[1])
    return '%8.2fs %s:%s:%s %s' % (t - t0, kind, s[0], s[1], s[2])


def diff(good, bad, top=15, noise=None, out=sys.stdout, trigger_re=DEFAULT_TRIGGER):
    noise = load_noise() if noise is None else noise
    w = out.write
    ge, be = events(good), events(bad)
    gt0 = good.meta.get('t0_wine') or good.first_t or 0
    bt0 = bad.meta.get('t0_wine') or bad.first_t or 0
    gkeys = set((k, s, r) for _, k, s, r, _ in ge)
    gsigs = collections.defaultdict(set)
    for _, k, s, r, _ in ge:
        gsigs[(k, s)].add(r)
    bkeys = set((k, s, r) for _, k, s, r, _ in be)
    btrig = find_trigger(bad, trigger_re)
    gtrig = find_trigger(good, trigger_re)
    w('== fault diff\ngood: %s (%d events)\nbad:  %s (%d events)\n' % (good.path, len(ge), bad.path, len(be)))
    w('trigger in bad:  %s\n' % ('%s at %.2f s: %s' % (btrig['kind'], btrig['t'] - bt0, btrig['text'])
                                 if btrig else 'none'))
    w('trigger in good: %s\n' % ('%s at %.2f s: %s' % (gtrig['kind'], gtrig['t'] - gt0, gtrig['text'])
                                 if gtrig else 'none'))
    tlimit = btrig['t'] if btrig else float('inf')

    def keep(e, run):
        return not noisy(noise, show_event(run, e, 0))

    exc_only = [e for e in be if e[1] == 'exc' and (e[1], e[2], e[3]) not in gkeys and e[0] <= tlimit + 2]
    if exc_only:
        w('\nEXCEPTIONS only in the bad run:\n')
        for e in dedup_events(exc_only)[:top]:
            w('  %s\n' % show_event(bad, e, bt0))
    flips = [e for e in be if e[1] == 'call' and e[0] <= tlimit and (e[1], e[2]) in gsigs
             and e[3] not in gsigs[(e[1], e[2])] and keep(e, bad)]
    if flips:
        w('\nRESULT FLIPS (same call, other result in the good run; bad run order):\n')
        for e in dedup_events(flips)[:top]:
            w('  %s   [good: %s]\n' % (show_event(bad, e, bt0), '/'.join(sorted(gsigs[(e[1], e[2])]))))
    new = [e for e in be if e[0] <= tlimit and (e[1], e[2]) not in gsigs and e[1] != 'load' and keep(e, bad)]
    newfail = [e for e in new if e[1] != 'call' or e[3] != 'ok']
    if newfail:
        w('\nFIRST BAD-ONLY failures/errors (not in the good run at all):\n')
        for e in dedup_events(newfail)[:top]:
            w('  %s\n' % show_event(bad, e, bt0))
    gonly = [e for e in ge if e[1] in ('call', 'load') and (e[1], e[2], e[3]) not in bkeys
             and (e[1], e[2]) not in set((k, s) for _, k, s, _, _ in be) and keep(e, good)]
    if gonly:
        w('\nGOOD-ONLY lookups/loads (the bad run never made them; good run order):\n')
        for e in dedup_events(gonly)[:top]:
            w('  %s\n' % show_event(good, e, gt0))
    bonly_loads = [e for e in be if e[1] == 'load' and (e[1], e[2]) not in gsigs and e[0] <= tlimit]
    if bonly_loads:
        w('\nBAD-ONLY module loads: %s\n' % ', '.join(dedup(e[2][0] for e in bonly_loads)[:top]))
    return dict(exc=len(exc_only), flips=len(flips), new=len(newfail), gonly=len(gonly))


def dedup_events(evs):
    seen, out = set(), []
    for e in evs:
        key = (e[1], e[2], e[3])
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


# ---------------------------------------------------------------- run
class XWatch(threading.Thread):
    """Top-level maps and _NET_WM_PING answers of the program's windows."""

    def __init__(self):
        super().__init__(daemon=True)
        from Xlib import display, X
        self.X = X
        self.d = display.Display()
        self.root = self.d.screen().root
        self.root.change_attributes(event_mask=X.SubstructureNotifyMask)
        self.events = []
        self.pongs = {}
        self.lock = threading.Lock()
        self.a_proto = self.d.intern_atom('WM_PROTOCOLS')
        self.a_ping = self.d.intern_atom('_NET_WM_PING')
        self.a_pid = self.d.intern_atom('_NET_WM_PID')

    def name_of(self, w):
        try:
            for atom in ('_NET_WM_NAME', 'WM_NAME'):
                prop = w.get_full_property(self.d.intern_atom(atom), self.X.AnyPropertyType)
                if prop and prop.value:
                    v = prop.value
                    return v.decode('utf-8', 'replace') if isinstance(v, bytes) else str(v)
        except Exception:
            pass
        return ''

    def run(self):
        X = self.X
        while True:
            e = self.d.next_event()
            t = time.monotonic()
            if e.type == X.MapNotify:
                with self.lock:
                    self.events.append((t, 'map', e.window.id, self.name_of(e.window)))
            elif e.type == X.UnmapNotify:
                with self.lock:
                    self.events.append((t, 'unmap', e.window.id, ''))
            elif e.type == X.ClientMessage and e.client_type == self.a_proto:
                data = e.data[1]
                if data[0] == self.a_ping:
                    with self.lock:
                        self.pongs[data[2]] = t

    def mapped(self, regex, after=0):
        with self.lock:
            for t, kind, wid, name in self.events:
                if kind == 'map' and t >= after and re.search(regex, name):
                    return t, wid, name
        return None

    def ping_targets(self, pids):
        """Managed windows of our unix pids that take _NET_WM_PING."""
        out = []
        try:
            for w in self.root.query_tree().children:
                p = w.get_full_property(self.a_pid, self.X.AnyPropertyType)
                if not p or not len(p.value) or p.value[0] not in pids:
                    continue
                if w.get_attributes().map_state != self.X.IsViewable:
                    continue
                protos = w.get_wm_protocols() or []
                if self.a_ping in protos:
                    out.append(w)
        except Exception:
            pass
        return out

    def ping(self, w):
        from Xlib.protocol import event
        stamp = int(time.monotonic() * 1000) & 0x7fffffff
        ev = event.ClientMessage(window=w, client_type=self.a_proto,
                                 data=(32, [self.a_ping, stamp, w.id, 0, 0]))
        w.send_event(ev, event_mask=0)
        self.d.flush()
        return stamp


def prefix_procs(prefix, keep=()):
    """{unix pid: comm} of processes with WINEPREFIX=prefix in their environment."""
    out = {}
    needle = b'WINEPREFIX=' + prefix.encode() + b'\0'
    for name in os.listdir('/proc'):
        if not name.isdigit() or int(name) in keep:
            continue
        try:
            with open('/proc/%s/environ' % name, 'rb') as f:
                if needle in f.read():
                    out[int(name)] = open('/proc/%s/comm' % name).read().strip()
        except OSError:
            pass
    return out


SERVICE_COMMS = re.compile(r'^(wineserver|services\.exe|winedevice\.exe|plugplay\.exe|explorer\.exe|svchost\.exe|'
                           r'rpcss\.exe|winemenubuilder|conhost\.exe|wineboot\.exe|start\.exe|tabtip\.exe|'
                           r'python3?|sh|bash|dllmgr)', re.I)


def ancestors():
    keep, pid = set(), os.getpid()
    while pid > 1:
        keep.add(pid)
        try:
            pid = int(open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return keep


def wine_env(a):
    env = dict(os.environ, WINEPREFIX=os.path.realpath(a.prefix))
    if a.runtime:
        rt = os.path.realpath(a.runtime)
        env.update(WINEARCH='wow64', WINELOADER=rt + '/bin/wine', WINESERVER=rt + '/bin/wineserver')
    for kv in a.env:
        k, _, v = kv.partition('=')
        env[k] = v
    return env


def wine_bin(a, name):
    return os.path.join(os.path.realpath(a.runtime), 'bin', name) if a.runtime else os.path.join(a.wine, name)


def set_relay(a, env, funcs):
    """RelayInclude in HKCU\\Software\\Wine\\Debug (Wine reads relay filters only from there)."""
    key = r'HKCU\Software\Wine\Debug'
    q = subprocess.run([wine_bin(a, 'wine'), 'reg', 'query', key, '/v', 'RelayInclude'], env=dict(env, WINEDEBUG='-all'),
                       capture_output=True, text=True, errors='replace')
    old = None
    m = re.search(r'RelayInclude\s+REG_SZ\s+(.*)', q.stdout)
    if m:
        old = m.group(1).strip()
    if funcs:
        subprocess.run([wine_bin(a, 'wine'), 'reg', 'add', key, '/v', 'RelayInclude', '/d', ';'.join(funcs), '/f'],
                       env=dict(env, WINEDEBUG='-all'), capture_output=True)
    return old


def restore_relay(a, env, old):
    key = r'HKCU\Software\Wine\Debug'
    cmd = ([wine_bin(a, 'wine'), 'reg', 'add', key, '/v', 'RelayInclude', '/d', old, '/f'] if old is not None else
           [wine_bin(a, 'wine'), 'reg', 'delete', key, '/v', 'RelayInclude', '/f'])
    subprocess.run(cmd, env=dict(env, WINEDEBUG='-all'), capture_output=True)
    subprocess.run([wine_bin(a, 'wineserver'), '-w'], env=env, capture_output=True, timeout=60)


def kill_prefix(a, env, keep):
    for srv in dedup([wine_bin(a, 'wineserver'), os.path.join(a.wine, 'wineserver')]):
        subprocess.run([srv, '-k'], env=env, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    for pid in prefix_procs(env['WINEPREFIX'], keep):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


class LogWatch(threading.Thread):
    """Tails wine.log for the trigger while the program runs."""

    def __init__(self, path, trigger_re):
        super().__init__(daemon=True)
        self.path, self.rx = path, re.compile(trigger_re) if trigger_re else None
        self.hit = None
        self.wpid = None
        self.stop = False

    def run(self):
        pos, buf = 0, b''
        while not self.stop and self.hit is None:
            try:
                with open(self.path, 'rb') as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos += len(chunk)
            except OSError:
                chunk = b''
            if not chunk:
                time.sleep(0.1)
                continue
            buf += chunk
            lines = buf.split(b'\n')
            buf = lines.pop()
            for raw in lines:
                line = raw.decode('utf-8', 'replace')
                if self.wpid is None and 'Loaded L"' in line and '.exe" at ' in line and ': native' in line:
                    m = PREFIX.match(line)
                    if m and m.group(2):
                        self.wpid = m.group(2)
                if 'wine: Unhandled' in line:
                    self.hit = ('unhandled', time.monotonic(), line.strip()[:200])
                    break
                if self.rx is not None and ':Call ' in line and self.rx.search(line):
                    m = CALL.match(PREFIX.match(line).group(4)) if PREFIX.match(line) else None
                    if m and TEXT_FUNCS.match(m.group(2)):
                        self.hit = ('dialog', time.monotonic(), line.strip()[:200])
                        if m and PREFIX.match(line).group(2):
                            self.wpid = PREFIX.match(line).group(2)
                        break


def winedbg_bt(a, env, wpid, out):
    """`bt all` of a running process (attach, print, detach)."""
    try:
        r = subprocess.run([wine_bin(a, 'wine'), 'winedbg', str(int(wpid, 16))], env=dict(env, WINEDEBUG='-all'),
                           input='bt all\ndetach\nquit\n', capture_output=True, text=True, errors='replace',
                           timeout=60)
        open(out, 'w').write(r.stdout + r.stderr)
    except (subprocess.TimeoutExpired, ValueError) as e:
        open(out, 'w').write('winedbg failed: %s\n' % e)


def cmd_run(a):
    if os.environ.get('DISPLAY', '') in ('', ':0', ':0.0'):
        sys.exit('fault.py: refusing DISPLAY %r (stand displays only)' % os.environ.get('DISPLAY'))
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd:
        sys.exit('fault.py run: no COMMAND')
    os.makedirs(a.out, exist_ok=True)
    env = wine_env(a)
    prefix = env['WINEPREFIX']
    keep = ancestors()
    kill_prefix(a, env, keep)
    funcs = PRESETS.get(a.relay, None)
    if funcs is None:
        funcs = [f for f in re.split(r'[;,\s]+', a.relay) if f]
    funcs = funcs + [f for f in re.split(r'[;,\s]+', a.relay_add or '') if f]
    old = set_relay(a, env, funcs) if funcs else None
    if funcs:
        subprocess.run([wine_bin(a, 'wineserver'), '-k'], env=env, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    chans = ['+timestamp', '+pid', '+seh', '+loaddll'] + (['+relay'] if funcs else []) + \
        [c for c in a.channels.split(',') if c]
    env['WINEDEBUG'] = ','.join(chans)
    log_path = os.path.join(a.out, 'wine.log')
    x = None
    try:
        x = XWatch()
        x.start()
    except Exception as e:
        print('fault.py: no X observer (%s): no hang detection or steps' % e, file=sys.stderr)
    log = open(log_path, 'wb')
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, env=env, cwd=a.cwd or None, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    watch = LogWatch(log_path, a.trigger)
    watch.start()
    meta = dict(command=cmd, prefix=prefix, runtime=a.runtime, winedebug=env['WINEDEBUG'], relay=funcs,
                trigger_re=a.trigger, t0_wine=t0)
    trig = None
    steps = list(zip(a.step, a.do + [''] * (len(a.step) - len(a.do))))
    after_step = t0
    deadline = t0 + a.timeout
    pings = {}
    next_ping = t0 + 5
    exit_code = None
    while time.monotonic() < deadline:
        time.sleep(0.2)
        now = time.monotonic()
        if watch.hit:
            trig = dict(kind=watch.hit[0], t_wine=watch.hit[1], text=watch.hit[2])
            break
        if exit_code is None and proc.poll() is not None:
            exit_code = proc.returncode
            meta['launcher_exit'] = exit_code
        if exit_code is not None:
            alive = [c for c in prefix_procs(prefix, keep).values() if not SERVICE_COMMS.match(c)]
            if not alive:
                if exit_code:
                    trig = dict(kind='exit', t_wine=now, text='exit code %d' % exit_code)
                break
        if x is not None and steps:
            regex, do = steps[0]
            hit = x.mapped(regex, after_step)
            if hit and now - hit[0] >= a.settle:
                steps.pop(0)
                if do:
                    subprocess.run(do, shell=True, env=dict(env, WID=str(hit[1])))
                after_step = time.monotonic()
        if x is not None and a.hang and now >= next_ping:
            next_ping = now + 2
            ours = set(prefix_procs(prefix, keep))
            for w in x.ping_targets(ours):
                stamp = pings.get(w.id)
                if stamp is None:
                    pings[w.id] = (x.ping(w), now)
                    continue
                sent, t_sent = stamp
                with x.lock:
                    answered = x.pongs.get(sent)
                if answered:
                    pings[w.id] = (x.ping(w), now)
                elif now - t_sent > a.hang:
                    trig = dict(kind='hang', t_wine=t_sent, text='window 0x%x "%s" did not answer _NET_WM_PING for '
                                '%.0f s' % (w.id, x.name_of(w), now - t_sent))
                    break
            if trig:
                break
    else:
        trig = trig or (dict(kind='timeout', t_wine=time.monotonic(), text='timeout %ds' % a.timeout)
                        if a.timeout_is_trigger else None)
    meta['trigger'] = trig
    if trig and trig['kind'] in ('dialog', 'unhandled', 'hang', 'timeout'):
        time.sleep(a.after)
        subprocess.run(['import', '-window', 'root', '-resize', '50%', os.path.join(a.out, 'trigger.png')],
                       stderr=subprocess.DEVNULL)
        if a.bt and watch.wpid:
            winedbg_bt(a, env, watch.wpid, os.path.join(a.out, 'bt.txt'))
    meta['stopped_by_us'] = proc.poll() is None
    meta['exit_code'] = proc.returncode if proc.poll() is not None else None
    watch.stop = True
    kill_prefix(a, env, keep)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
    log.close()
    if funcs:
        restore_relay(a, env, old)
        kill_prefix(a, env, keep)
    meta['wall_s'] = round(time.monotonic() - t0, 1)
    if x is not None:
        with x.lock:
            meta['windows'] = [(round(t - t0, 2), k, '0x%x' % wid, n) for t, k, wid, n in x.events]
    json.dump(meta, open(os.path.join(a.out, 'meta.json'), 'w'), indent=1)
    run = Run(log_path, meta)
    with open(os.path.join(a.out, 'report.txt'), 'w') as f:
        good = load_run(a.good) if a.good else None
        report(run, a.trigger, good=good, window=a.window, top=a.top, out=f)
    sys.stdout.write(open(os.path.join(a.out, 'report.txt')).read())
    print('\n(run took %.0f s wall; files in %s)' % (meta['wall_s'], a.out))
    return 0 if trig is None else 3


def load_run(d):
    log = os.path.join(d, 'wine.log') if os.path.isdir(d) else d
    meta_path = os.path.join(os.path.dirname(log), 'meta.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    return Run(log, meta)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run', help='launch with fault logging, stop at the trigger, report')
    r.add_argument('--out', required=True)
    r.add_argument('--prefix', required=True)
    r.add_argument('--runtime', help='private runtime dir (sets WINEARCH=wow64, WINELOADER, WINESERVER)')
    r.add_argument('--wine', default='/opt/wine-stable/bin', help='stock Wine bin dir (no --runtime)')
    r.add_argument('--cwd')
    r.add_argument('--env', action='append', default=[], help='VAR=VALUE for the program')
    r.add_argument('--trigger', default=DEFAULT_TRIGGER, help='regex for error text shown by the program')
    r.add_argument('--relay', default='lookups', help='lookups | ui | none | func;func;...')
    r.add_argument('--relay-add', help='more functions for RelayInclude')
    r.add_argument('--channels', default='', help='more WINEDEBUG channels, e.g. +reg,warn+file')
    r.add_argument('--timeout', type=int, default=180)
    r.add_argument('--timeout-is-trigger', action='store_true', help='report at the timeout as if it failed there')
    r.add_argument('--hang', type=float, default=0, help='seconds without a _NET_WM_PING answer = hang (0: off)')
    r.add_argument('--after', type=float, default=2, help='seconds to keep running after the trigger')
    r.add_argument('--no-bt', dest='bt', action='store_false', help='no winedbg bt all at the trigger')
    r.add_argument('--step', action='append', default=[], help='window name regex to wait for, then --do')
    r.add_argument('--do', action='append', default=[], help='shell command for the matching --step ($WID)')
    r.add_argument('--settle', type=float, default=2, help='seconds after a --step window maps before its --do')
    r.add_argument('--good', help='earlier good run dir for the ranking')
    r.add_argument('--window', type=float, default=30)
    r.add_argument('--top', type=int, default=10)
    r.add_argument('command', nargs=argparse.REMAINDER)
    p = sub.add_parser('report', help='report of an earlier run dir (or a wine.log)')
    p.add_argument('dir')
    p.add_argument('--good')
    p.add_argument('--trigger', default=DEFAULT_TRIGGER)
    p.add_argument('--window', type=float, default=30)
    p.add_argument('--top', type=int, default=10)
    d = sub.add_parser('diff', help='first divergence between a good and a bad run')
    d.add_argument('good')
    d.add_argument('bad')
    d.add_argument('--trigger', default=DEFAULT_TRIGGER)
    d.add_argument('--top', type=int, default=15)
    a = ap.parse_args(argv)
    if a.cmd == 'run':
        return cmd_run(a)
    if a.cmd == 'report':
        run = load_run(a.dir)
        good = load_run(a.good) if a.good else None
        report(run, a.trigger, good=good, window=a.window, top=a.top)
        return 0
    good, bad = load_run(a.good), load_run(a.bad)
    diff(good, bad, top=a.top, trigger_re=a.trigger)
    return 0


if __name__ == '__main__':
    sys.exit(main())
