#!/usr/bin/env python3
"""wineserver round trips from a `wineserver -f -d1` log (#87).

usage: server-report.py SERVER.LOG [--top N]

SERVER.LOG is what tools/perf/startup.py --server-trace writes. Counts the
requests (not the replies) per request name and per client thread, and the
processes the threads belong to (from init_first_thread / init_thread and
the process image names in new_process requests when present).
"""
import argparse, collections, re, sys

REQ = re.compile(r'^([0-9a-f]{4}): ([a-z_0-9]+)\((.*)$')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log')
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    names = collections.Counter()
    threads = collections.Counter()
    per_thread_names = collections.defaultdict(collections.Counter)
    total = 0
    with open(a.log, errors='replace') as f:
        for line in f:
            m = REQ.match(line)
            if not m or m.group(3).startswith(') ='):
                continue  # replies: "name() = STATUS {...}"
            tid, name = m.group(1), m.group(2)
            total += 1
            names[name] += 1
            threads[tid] += 1
            per_thread_names[tid][name] += 1
    print('# %s: %d requests (one round trip each)' % (a.log, total))
    print('\n## per request')
    for n, c in names.most_common(a.top):
        print('%7d %5.1f%%  %s' % (c, 100.0 * c / total, n))
    print('\n## per client thread (top requests of each)')
    for t, c in threads.most_common(12):
        top = ', '.join('%s %d' % kv for kv in per_thread_names[t].most_common(4))
        print('%7d  thread %s: %s' % (c, t, top))


if __name__ == '__main__':
    sys.exit(main())
