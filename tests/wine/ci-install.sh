#!/usr/bin/env bash
# Install CI packages with hard limits: every network call has a timeout and a
# stalled apt/dpkg run is killed, dumped and retried once, so a bad mirror
# costs minutes, not the job. Usage: ci-install.sh [--winehq] package...
set -uo pipefail
PS4='+ $(date +%T) '
winehq=0
if [ "${1:-}" = --winehq ]; then winehq=1; shift; fi
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
    sudo apt-get "${apt_opts[@]}" update -qq &&
        sudo apt-get "${apt_opts[@]}" install -y -qq "$@"
}

dump() {
    echo "::group::diagnostics after stalled install"
    ps -eo pid,ppid,etime,stat,wchan:20,args --forest | grep -E 'apt|dpkg|curl|http' | grep -v grep
    tail -n 20 /var/log/apt/term.log /var/log/dpkg.log 2>/dev/null
    echo "::endgroup::"
}

for n in 1 2; do
    # Normal install is 60-80 s; 150 s is about 2x that, two attempts.
    if timeout -k 10 150 bash -c "$(declare -f attempt); $(declare -p apt_opts winehq); attempt $*"; then exit 0; fi
    echo "::warning::install attempt $n failed or stalled"
    dump
    sudo pkill -9 -x -e 'apt-get|dpkg|apt' || true
    sudo dpkg --configure -a || true
done
exit 1
