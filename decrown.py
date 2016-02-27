#!/usr/bin/env python
# Copyright (C) 2016 Mansour Behabadi <mansour@oxplot.com>

import re
import sys

data = sys.stdin.buffer.read()
def sub(p):
  global data
  data = re.sub(p, b'', data, 1, re.M)

sub(br'^%%[^%]*?/Producer\s*\(\x50\x72\x69\x6e\x63\x65[^%]*?endobj$\n')
sub(br'^%%[^%]*?/Contents\s*\(This document[^%]*?endobj$\n')
sub(br'^%%[^%]*?0\.2314 0\.0471 0\.3765[^%]*?endobj$\n')

sys.stdout.buffer.write(data)
