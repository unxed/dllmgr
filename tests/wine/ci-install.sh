#!/usr/bin/env bash
# Bound network/package operations and preserve the last URL/phase on failure.
set -euo pipefail
PS4='+ ${EPOCHREALTIME} '
attempt_mode=0
if [ "${1:-}" = --attempt ]; then attempt_mode=1; shift; fi
winehq=0
if [ "${1:-}" = --winehq ]; then winehq=1; shift; fi
[ "$#" -gt 0 ] || { echo 'usage: ci-install.sh [--winehq] package...' >&2; exit 2; }
apt_opts=(-o Acquire::Retries=3 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 -o DPkg::Lock::Timeout=60)

attempt() {
    set -x
    if [ "$winehq" = 1 ]; then
        sudo dpkg --add-architecture i386
        sudo mkdir -pm755 /etc/apt/keyrings
        curl -fsSL --retry 3 --connect-timeout 15 --max-time 60 https://dl.winehq.org/wine-builds/winehq.key \
            | sudo tee /etc/apt/keyrings/winehq-archive.key >/dev/null
        curl -fsSL --retry 3 --connect-timeout 15 --max-time 60 https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
            | sudo tee /etc/apt/sources.list.d/winehq-noble.sources >/dev/null
    fi
    sudo apt-get "${apt_opts[@]}" update -q
    # One -q retains download URLs, unlike -qq; full output stays in the log.
    sudo apt-get "${apt_opts[@]}" install -y -q "$@"
}

# A separate strict shell makes setup/pipeline errors fatal even though the
# parent tests timeout's exit code. Package arguments never become shell code.
if [ "$attempt_mode" = 1 ]; then attempt "$@"; exit; fi
logs=${RUNNER_TEMP:-${TMPDIR:-/tmp}}/dllmgr-ci-install
mkdir -p "$logs"
setup=()
[ "$winehq" = 0 ] || setup=(--winehq)
for n in 1 2 3; do
    log=$logs/attempt-$n.log
    limit=150
    if [ "$n" = 3 ]; then
        # The runner's Azure Ubuntu mirror sometimes stalls for an hour
        # (2026-11-10: three runs in a row): last attempt via archive.ubuntu.com.
        echo "::warning::switching apt from azure.archive.ubuntu.com to archive.ubuntu.com"
        sudo sed -i 's#azure\.archive\.ubuntu\.com#archive.ubuntu.com#g' \
            /etc/apt/sources.list /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list 2>/dev/null || true
        limit=300
    fi
    if timeout -k 5 "$limit" bash "${BASH_SOURCE[0]}" --attempt "${setup[@]}" "$@" >"$log" 2>&1; then
        tail -n 12 "$log"
        exit 0
    else
        rc=$?
    fi
    echo "::warning::install attempt $n failed (exit $rc); log: $log"
    tail -n 40 "$log"
    {
        ps -eo pid,ppid,etime,stat,wchan:20,args --forest | grep -E 'apt|dpkg|curl|http' | grep -v grep || true
        find /var/cache/apt/archives/partial -maxdepth 1 -type f -printf '%f %s bytes\n' 2>/dev/null || true
        tail -n 20 /var/log/apt/term.log /var/log/dpkg.log 2>/dev/null || true
    } | tee "$logs/diagnostics-$n.log"
    if [ "$rc" = 124 ] || [ "$rc" = 137 ]; then
        # CI runners are disposable; timeout may leave sudo's separate group.
        sudo pkill -9 -x -e 'apt-get|dpkg|apt' || true
        if ! timeout -k 2 12 sudo dpkg --configure -a >"$logs/recovery-$n.log" 2>&1; then
            tail -n 20 "$logs/recovery-$n.log"
            echo '::error::dpkg recovery failed; not retrying a broken package state'
            exit 1
        fi
    fi
done
exit 1
