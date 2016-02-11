#!/usr/bin/env python
# tree_ot.py - Tree based operational transformation library
# Copyright (C) 2015 Mansour Behabadi <mansour@oxplot.com>
#
# FIXME Use of generators and recursion in general can lead to hitting
#       the recursion limits imposed by python. The code here should be
#       rewritten in a non-recursive manner and even after that, there
#       should be a limit to how large an operation can be, both in
#       actual byte size and in depth.

import copy
from itertools import chain

# There are two kinds of nodes: tree and character
#  - A tree node is analogous to an HTML element like <table></table>
#  - A chars node is a series of chars like 'ABCDE'
#
# ['k', n, op, attrs]       -> keep n nodes, opt. tree sub-op and # attrs
# ['i', chars, op, attrs]   -> insert chars/tree - op & attrs as # keep
# ['d', n]                  -> delete n nodes, if n == 0, delete inserts
# ['a', starts, ends]       -> annotation boundary

class TransformError(Exception):
  pass

class OpLoadError(Exception):
  pass

class ComposeError(Exception):
  pass

class _Noop:
  __slots__ = ()

  def __len__(self):
    return 0
Noop = _Noop()

class Keep:
  __slots__ = ('n', 'op', 'attrs')

  def __init__(self, n, op = None, attrs = None):
    self.n, self.op, self.attrs = n, op, attrs

  def __len__(self):
    return self.n

class Insert:
  __slots__ = ('chars', 'op', 'attrs')
  def __init__(self, chars = None, op = None, attrs = None):
    'chars and (op, attrs) are mutually exclusive.'
    self.chars, self.op, self.attrs = chars, op, attrs

  def __len__(self):
    return len(self.chars or '') or 1

class Delete:
  __slots__ = ('n')

  def __init__(self, n):
    self.n = n

  def __len__(self):
    return self.n or 1

def _expanded(fn):
  def _fn(*args, **kwargs):
    return list(fn(*args, **kwargs))
  return _fn

@_expanded
def load_op(op):
  for el in op:
    el_type = el[0]
    if el_type in ('k', 'i'):
      el_op, attrs = None, None
      if len(el) > 2:
        if el[2] is not None:
          el_op = load_op(el[2]) or None
        if len(el) > 3 and el[3] is not None:
          attrs = el[3]
    if el_type == 'k':
      yield Keep(n=el[1], op=el_op, attrs=attrs)
    elif el_type == 'i':
      yield Insert(chars=el[1], op=el_op, attrs=attrs)
    elif el_type == 'd':
      yield Delete(n=el[1])
    else:
      raise OpLoadError('Invalid el_type of %r' % el_type)

@_expanded
def dump_op(op):
  for el in op:
    el_type = type(el)
    if el_type in (Keep, Insert) and el.op is not None:
      el_op = dump_op(el.op) or None
    else:
      el_op = None
    if el_type is Keep:
      if el.attrs is not None:
        yield ['k', el.n, el_op, el.attrs]
      elif el_op is not None:
        yield ['k', el.n, el_op]
      else:
        yield ['k', el.n]
    elif el_type is Insert:
      if el.attrs is not None:
        yield ['i', el.chars, el_op, el.attrs]
      elif el_op is not None:
        yield ['i', el.chars, el_op]
      else:
        yield ['i', el.chars]
    elif el_type is Delete:
      yield ['d', el.n]
    else:
      raise OpLoadError('Invalid el_type of %r' % el_type)

def op_len(op):
  'Determine the length of doc this op can be composed to.'
  length = 0
  for el in op:
    if type(el) in (Keep, Delete):
      length += el.n
  return length

@_expanded
def eliminate_zero_del(op):
  'Eliminate zero-length op elements recursively.'
  for el in op:
    el_type = type(el)
    if el_type is Keep and el.op is not None:
      el_op = eliminate_zero_del(el.op) or None
      yield Keep(n=el.n, op=el_op, attrs=el.attrs)
    elif el_type is Delete and el.n == 0:
      continue
    else:
      yield el

class PairState:
  __slots__ = ('a', 'b', 'a_rem', 'b_rem', 'reverse')
  def consume_overlap(self):
    overlap = self.overlap
    self.a_rem, self.b_rem = self.a_rem - overlap, self.b_rem - overlap

  @property
  def overlap(self):
    return min(self.a_rem, self.b_rem)

def op_pair_processor(proc):
  'Create a op pair stream reader.'
  @_expanded
  def fn(op_a, op_b, reverse = False):
    out_buffer = Noop
    p = PairState()
    op_a, op_b = map(iter, (op_a, op_b))
    p.a = next(op_a, Noop)
    p.b = next(op_b, Noop)
    p.a_rem, p.b_rem = len(p.a) or 1, len(p.b) or 1
    p.reverse = reverse

    while not (p.a is Noop and p.b is Noop):

      for el, merge in proc(p):
        out_type, el_type = type(out_buffer), type(el)
        can_merge = merge and out_type == el_type and (
          el_type is not Keep or not any([el.op, out_buffer.op])
        ) and (
          el_type is not Insert or (out_buffer.chars and el.chars)
        )
        if can_merge:
          if out_type in (Keep, Delete):
            out_buffer.n += el.n
          elif out_type is Insert:
            out_buffer.chars += el.chars
        else:
          if out_buffer is not Noop:
            yield out_buffer
          out_buffer = copy.copy(el)

      # Get the next element from op stream if needed

      if p.a_rem == 0:
        p.a = next(op_a, Noop)
        p.a_rem = len(p.a) or 1
      if p.b_rem == 0:
        p.b = next(op_b, Noop)
        p.b_rem = len(p.b) or 1

    if out_buffer is not Noop:
      yield out_buffer

  return fn

@op_pair_processor
def _transform(p):
  '''Transform operations.

  When p.reverse is set to True, p.a and p.b are reversed. This allows
  significant code sharing. Areas where this reversion doesn't work,
  special code checks for server and makes the appropriate decision.
  '''
  server = not p.reverse

  if type(p.a) is Keep and type(p.b) is Keep:
    if p.a.op is not None and p.b.op is not None:
      if server:
        op = s_transform(p.a.op, p.b.op)
      else:
        op = c_transform(p.b.op, p.a.op)
    else:
      op = p.a.op
      if op:
        op = eliminate_zero_del(op)
    s_attrs = p.a.attrs if server else p.b.attrs
    c_attrs = p.b.attrs if server else p.a.attrs
    attrs = dict(chain(
      (c_attrs or {}).items(), (s_attrs or {}).items()
    )) if s_attrs or c_attrs else None
    yield Keep(n=p.overlap, op=op, attrs=attrs), True
    p.consume_overlap()

  elif type(p.a) is Keep and type(p.b) is Insert:
    yield Keep(n=len(p.b)), True
    p.b_rem = 0

  elif type(p.a) is Keep and type(p.b) is Delete:
    if p.b.n == 0:
      p.b_rem = 0
    else:
      p.consume_overlap()

  elif type(p.a) is Insert and type(p.b) is Insert:
    if server:
      yield Keep(n=len(p.b)), True
      p.b_rem = 0
    else:
      yield p.a, True
      p.a_rem = 0

  elif type(p.a) is Insert and type(p.b) is Keep:
    yield p.a, True
    p.a_rem = 0

  elif type(p.a) is Insert and type(p.b) is Delete:
    if not (p.b.n == 0 or p.b_rem < p.b.n):
      yield p.a, True
    p.a_rem = 0

  elif type(p.a) is Delete and type(p.b) is Delete:
    if p.a.n == 0 and p.b.n == 0:
      if server:
        p.b_rem = 0
      else:
        p.a_rem = 0
    elif p.a.n == 0 or p.b.n == 0:
      if p.a.n == 0:
        p.a_rem = 0
      if p.b.n == 0:
        p.b_rem = 0
    else:
      p.consume_overlap()

  elif type(p.a) is Delete and type(p.b) is Keep:
    if p.a.n == 0:
      p.a_rem = 0
    else:
      yield Delete(n=p.overlap), p.a_rem < p.a.n
      p.consume_overlap()

  elif type(p.a) is Delete and type(p.b) is Insert:
    if p.a.n == 0 or p.a_rem < p.a.n:
      yield Delete(n=len(p.b)), True
    else:
      yield Keep(n=len(p.b)), True
    p.b_rem = 0

  elif p.a is Noop and type(p.b) is Insert:
    yield Keep(n=len(p.b)), True
    p.b_rem = 0

  elif type(p.a) is Insert and p.b is Noop:
    yield p.a, True
    p.a_rem = 0

  elif p.a is Noop and type(p.b) is Delete and p.b.n == 0:
    p.b_rem = 0

  elif type(p.a) is Delete and p.b is Noop and p.a.n == 0:
    p.a_rem = 0

  else:
    raise TransformError('%r %r' % (p.a, p.b))

def s_transform(op_s, op_c, **kwargs):
  return _transform(op_s, op_c, **kwargs)

def c_transform(op_s, op_c, **kwargs):
  kwargs['reverse'] = True
  return _transform(op_c, op_s, **kwargs)

@op_pair_processor
def compose(p):

  if type(p.a) is Keep and type(p.b) is Keep:
    if p.a.op is not None and p.b.op is not None:
      op = compose(p.a.op, p.b.op)
    else:
      op = p.a.op or p.b.op or None
    attrs = dict(chain(
      (p.a.attrs or {}).items(), (p.b.attrs or {}).items()
    )) if p.a.attrs or p.b.attrs else None
    yield Keep(n=p.overlap, op=op, attrs=attrs), True
    p.consume_overlap()

  elif type(p.a) is Keep and type(p.b) is Delete:
    if p.b.n == 0:
      yield p.b, False
      p.b_rem = 0
    else:
      yield Delete(n=p.overlap), p.b_rem < p.b.n
      p.consume_overlap()

  elif type(p.a) is Insert and type(p.b) is Delete:
    if p.b.n == 0:
      yield p.b, False
      p.b_rem = 0
    else:
      p.consume_overlap()

  elif type(p.a) is Insert and type(p.b) is Keep:
    if p.a.chars is not None and p.b.op is not None:
      raise ComposeError('cannot Keep(op) an Insert(chars)')
    if p.a.op is not None and p.b.op is not None:
      op = compose(p.a.op, p.b.op)
    else:
      op = p.a.op or p.b.op or None
    if p.a.chars:
      start = len(p.a.chars) - p.a_rem
      yield Insert(chars=p.a.chars[start:start + p.overlap]), True
    else:
      attrs = dict(chain(
        (p.a.attrs or {}).items(), (p.b.attrs or {}).items()
      )) if p.a.attrs or p.b.attrs else None
      yield Insert(op=op, attrs=attrs), True
    p.consume_overlap()

  elif type(p.a) is Delete:
    yield p.a, p.a.n > 0 and p.a_rem < p.a.n
    p.a_rem = 0

  elif type(p.b) is Insert:
    yield p.b, True
    p.b_rem = 0

  elif p.a is Noop and type(p.b) is Delete and p.b.n == 0:
    yield p.b, False
    p.b_rem = 0

  else:
    raise ComposeError('%r %r' % (p.a, p.b))
