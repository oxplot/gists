# dump-ssl.py - Dump SSL socket data in both directions to stderr
# Copyright (C) 2011 Mansour Behabadi <mansour@oxplot.com>

import ssl
realssl = ssl.SSLSocket

class SSLSocketDebugger(realssl):
  def __init__(self, *args, **kwargs):
    realssl.__init__(self, *args, **kwargs)

  def send(self, *args, **kwargs):
    data = kwargs.get('data', None) or args[0]
    sys.stderr.write(data)
    return realssl.send(self, *args, **kwargs)

  def read(self, *args, **kwargs):
    data = realssl.read(self, *args, **kwargs)
    sys.stderr.write(data)
    return data

#ssl.SSLSocket = SSLSocketDebugger #uncomment to see SSL traffic
