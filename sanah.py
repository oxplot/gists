#!/usr/bin/env python2
# sanah - Strictly Non-Human random password generator
#
# Copyright (C) 2011 by Mansour Behabadi <mansour@oxplot.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 
import Crypto.Random
import sys
import struct
 
if len(sys.argv) < 3:
  print "Usage: sanah <[@][0][a][A]> <length>"
  exit(0)
spec, length = sys.argv[1:3]
length = int(length)
 
chars = ''
if '@' in spec:
  chars += r'#@%^.'
if '0' in spec:
  chars += '0123456789'
if 'a' in spec:
  chars += 'abcdefghijklmnopqrstuvwxyz'
if 'A' in spec:
  chars += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
if not chars:
  print "You must pick at least one type of chars"
  exit(1)
 
gen = Crypto.Random.new()
rnd = gen.read(length * 2)
print ''.join(map(lambda a: chars[a % len(chars)],
                  struct.unpack('%dH' % length, rnd)))
gen.close()
