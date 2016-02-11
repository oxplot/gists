#!/bin/sh
# repdf.sh - Re-write PDF using ghostscript, compressing it in the
#            process.
# Copyright (C) 2011 Mansour Behabadi <mansour@oxplot.com>

OLDDATE=`stat -c %y "$1"`
DIR=`dirname "$1"`
TMPOUT="$1.tmp"

gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/screen \
   -dNOPAUSE -dQUIET -dBATCH -sOutputFile="$TMPOUT" "$1"
if [ $? = 0 ]
then
  mv "$TMPOUT" "$1"
  touch -d "$OLDDATE" "$1" &>/dev/null
  echo "$1 is cleaned."
else
  rm -f "$TMPOUT" &> /dev/null
  echo "$1 is skipped."
fi
