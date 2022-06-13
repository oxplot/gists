#!/bin/sh
# reflac.sh - Re-encode FLAC file, strip ID3 tags while preserving
#             timestamp.
# Copyright (C) 2022 Mansour Behabadi <mansour@oxplot.com>

OLDDATE=`stat -c %y "$1"`

id3v2 --delete-all "$1" >/dev/null &&
flac --best -V --force --silent "$1" >/dev/null &&
touch -d "$OLDDATE" "$1" >/dev/null &&

echo "$1 is cleaned."
