#!/bin/sh
# mkimg.sh DIR: three 1200x800 test JPEGs a/b/c (red/green/blue) in a fresh DIR
rm -f "$1"/*.jpg; mkdir -p "$1"; cd "$1" || exit 1
for n in a:red b:green c:blue; do
	convert -size 1200x800 xc:"${n#*:}" -gravity center -pointsize 200 -fill white -annotate 0 "${n%%:*}" "${n%%:*}.jpg"
done
