#!/bin/sh
# as-seen.sh IN.png OUT.png [SCALE]: what a fractionally scaled panel shows of
# a screenshot of the X screen (default 0.625: 3072x1728 -> 1920x1080, the
# owner's Cinnamon setup, docs/owner-machine.md). ASSUMPTION, not verified:
# bilinear filter (ImageMagick Triangle). The real filter is in
# `xrandr --verbose` (Transform / filter) on the owner's machine.
set -eu
scale=${3:-0.625}
pct=$(python3 -c "print(float('$scale') * 100)")
convert "$1" -filter Triangle -resize "${pct}%" "$2"
