# Asynchronous task library
# Copyright (C) 2015 Mansour Behabadi <mansour@oxplot.com>

import sys
import threading

# Commonly used exception handlers

iden = lambda x: x
none = lambda x: None

class _Result(object):
  'Async result as returned by ado().'

  def __init__(self, fn, arg):
    self._exc = None
    self._fn = fn
    self.arg = arg
    self._thread = threading.Thread(target=self._run)
    self._thread.daemon = True
    self._thread.start()

  def get(self, exc = None):
    '''Get return value of fn as passed to do() and ado().

    exc: If set, any exception raised in fn will be passed to it and
         its return value is returned, otherwise exception is raised.
    '''
    self._thread.join()
    if self._exc:
      if exc:
        return exc(self._exc)
      raise self._exc
    return self._ret

  def _run(self):
    try:
      self._ret = self._fn(self.arg)
    except:
      _, e, tb = sys.exc_info()
      self._exc = e.with_traceback(tb)

def do(fn, args, exc = None):
  '''Apply the fn to args and run all in parallel.

  Blocks until fn is applied to all args.
  args: List of arguments to fn
  exc: A function which if set is called with the exception raised by
       fn and its return value is used. If not set, the entire do()
       call fails with the first exception.
  '''
  return (r.get(exc=exc) for r in ado(fn, args))

def ado(fn, args):
  '''Async apply the fn to args and run all in parallel.

  Like do() except returns immediately with a list of Result objects.
  '''
  return [_Result(fn, arg) for arg in args]
