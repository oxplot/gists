#!/usr/bin/env python2
#
# namuse.py - Renames music files in mp3 and flac format.
# Copyright (C) 2010 Mansour Behabadi <mansour@oxplot.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import hashlib
import magic
import mutagen
import re
import os
from optparse import OptionParser, Option, OptionValueError
import shutil
import sys

########################################################################
# Globals
########################################################################

magicer = magic.open(magic.MAGIC_MIME)
magicer.load()
 
opts = None
posargs = None

########################################################################
# Main routine
########################################################################

def main():

  parseargs()
  destdir = posargs[-1]
  sources = posargs[:-1]

  if sources:
    for srcpath in sources:
      processsrc(srcpath, destdir)
  else:
    while True:
      try:
        srcpath = raw_input()
      except EOFError:
        break
      processsrc(srcpath, destdir)

########################################################################
# Process a single source path
########################################################################

def processsrc(srcpath, destdir):
  if os.path.isdir(srcpath):
    srcdir = srcpath
    for parent, dirs, files in os.walk(srcdir):
      for srcfile in files:
        srcpath = os.path.join(parent, srcfile)
        processfile(srcpath, destdir)
  else:
    processfile(srcpath, destdir)

########################################################################
# Process a single file
########################################################################

def processfile(srcpath, destdir):
  if not filesupported(srcpath):
    return
  try:
    destfile = getname(destdir, srcpath)
  except Exception:
    msg("ERROR and SKIPPED %s\n\n" % srcpath)
  else:
    destpath = os.path.join(destdir, destfile)
    opts.action(srcpath, destpath)

########################################################################
# Determines if a file type is supported by the program
########################################################################

def filesupported(src):
  ext = src.split('.')[-1].lower()
  if ext in ['mp3', 'flac', 'ogg']:
    return True
  mime = magicer.file(src).lower()
  return any(i in mime
             for i in ['audio/mpeg', 'audio/x-wav', 'audio/x-flac',
                       'application/ogg'])

########################################################################
# Get the new name for a music file.
########################################################################

def getname(dest, src):
  ext = src.split('.')[-1].lower()
  tags = readtags(src)
  names = []

  for title in tags['title']:
    for album in tags['album']:
      for artist in tags['artist']:
        names.append('%s-%s-%s.%s' % (artist, album, title, ext))
  for title in tags['title']:
    for artist in tags['artist']:
      names.append('%s-%s.%s' % (artist, title, ext))

  names.sort(cmp=(lambda a, b: cmp(len(a), len(b))))

  for name in names:
    if not os.path.exists(os.path.join(dest, name)):
      return name

  # if we can't use any of the names, use the hash

  md5 = hashlib.md5()
  f = open(src, 'r')
  try:
    while True:
      chunk = f.read(1000000)
      if chunk:
        md5.update(chunk)
      else:
        break
  finally:
    f.close()
  filehash = md5.hexdigest()

  name = "--%s-%s-%s-%s.%s" % (tags['artist'][0], tags['album'][0],
                               tags['title'][0], filehash, ext)
  return name

########################################################################
# Read the tags for the given music file.
########################################################################

def readtags(src):
  tags = mutagen.File(src)
  res = {'title': '', 'album': '', 'artist': ''}

  for el, k1, k2 in [('title', 'title', 'TIT2'),
                     ('album', 'album', 'TALB'),
                     ('artist', 'artist', 'TPE1')]:
    if k1 in tags and tags[k1]:
      res[el] = tags[k1][0]
    elif k2 in tags and tags[k2].text:
      res[el] = tags[k2].text[0]

  pat = r'[- \x00-\x1f*/:<>?\\|\x7f"`~={};!@_,./]+'

  for el in res:
    res[el] = re.sub(r"[']+", '', res[el])
    res[el] = res[el].replace('$', 's')
    res[el] = re.sub(pat, '_', res[el]).strip('_').lower()
    if not res[el]:
      res[el] = 'unknown'

  for el in res:
    cleaner = re.sub('_+', '_', killparen(res[el])).strip('_')
    if cleaner and cleaner != res[el]:
      res[el] = [cleaner.encode('utf-8'), res[el].encode('utf-8')]
    else:
      res[el] = [res[el].encode('utf-8')]
    
  return res

########################################################################
# Removes pairs of parens
########################################################################

def killparen(data):
  while any(i in data for i in '(['):
    m = re.search(r'[(\[]', data)
    if m:
      opencount = 1
      i = m.start() + 1
      for i in xrange(m.start() + 1, len(data)):
        if data[i] in '])':
          opencount -= 1
        elif data[i] in '([':
          opencount += 1
        if opencount == 0:
          break
      data = data[:m.start()] + '_' + data[i + 1:]
  return data

########################################################################
# Write to standard output with no buffer
########################################################################

def msg(m):
  sys.stdout.write(m)
  sys.stdout.flush()

########################################################################
# Different action types
########################################################################

def actionprint(src, dst):
  msg("%s\n  >> %s\n\n" % (src, dst))

def actionlink(src, dst):
  os.link(src, dst)
  msg("%s\n  >> %s [hard linked]\n\n" % (src, dst))

def actionsym(src, dst):
  os.symlink(src, dst)
  msg("%s\n  >> %s [sym linked]\n\n" % (src, dst))

def actionmove(src, dst):
  shutil.move(src, dst)
  msg("%s\n  >> %s [moved]\n\n" % (src, dst))

########################################################################
# parse command line arguments
########################################################################

def parseargs():

  usage = ( """usage: %prog [-m|-l|-s] [<src-path> ... ] <dest-dir>

By default, the program does not do anything besides outputting what the
new file names would be. Use one of the options below to perform an
action for each file.""")
  parser = OptionParser(usage=usage, version="%prog 0.6")

  parser.add_option("-l", "--hardlink", action="store_const",
                    dest="action", const=actionlink,
                    help="Create a hard link for each file")
  parser.add_option("-m", "--move", action="store_const",
                    dest="action", const=actionmove,
                    help="Move each file to new location")
  parser.add_option("-s", "--sym", action="store_const",
                    dest="action", const=actionsym,
                    help="Create a symbolic link for each file")

  global opts, posargs
  opts, posargs = parser.parse_args()

  if len(posargs) < 1:
    parser.error("destination directory is required")

  if not opts.action:
    opts.action = actionprint

########################################################################
if __name__ == '__main__':
  main()
