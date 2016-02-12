#!/usr/bin/env python
#
# cloop-decompress.py - Extract/Decompress cloop image to a raw image
#
# Copyright (C) 2012 Mansour Behabadi <mansour@oxplot.com>
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

from __future__ import unicode_literals
import sys
import os
import zlib
from struct import pack, unpack, calcsize

try:
  range = xrange
except:
  pass

CLOOP_HEADROOM = 128
CLOOP_HEAD_FMT = ('!%ds2I' % CLOOP_HEADROOM).encode('ascii')

def main(infile, outfile):

  # Read the cloop head

  pream, uncomp_buf_size, total_blocks = \
    unpack(CLOOP_HEAD_FMT, infile.read(calcsize(CLOOP_HEAD_FMT)))

  comp_buf_size = uncomp_buf_size + uncomp_buf_size // 1000 + 12 + 4
  total_offsets = total_blocks + 1

  # Read the block offsets

  offsets_fmt = ('!%dQ' % total_offsets).encode('ascii')
  offsets = unpack(offsets_fmt, infile.read(calcsize(offsets_fmt)))

  # Pipe the blocks through the decompressor and onto the output

  block_modulo = total_blocks // 10
  for i in range(total_blocks):
    size = offsets[i + 1] - offsets[i]
    if size < 0 or size > comp_buf_size:
      raise SystemExit(
        "Size %d for block %d (offset %d) wrong, corrupt data!"
        % (size, i, offsets[i])
      )
    comp_buf = infile.read(size)
    if len(comp_buf) != size:
      raise SystemExit("Error read %d data bytes" % size)
    uncomp_buf = zlib.decompress(comp_buf)
    outfile.write(uncomp_buf)

if __name__ == '__main__':

  if len(sys.argv) < 3:
    raise SystemExit("Usage: %s <infile> <outfile>" % sys.argv[0])

  infile, outfile = sys.argv[1:3]

  infile = sys.stdin if infile == '-' else open(infile, 'rb')
  outfile = sys.stdout if outfile == '-' else open(outfile, 'wb')

  main(infile, outfile)
