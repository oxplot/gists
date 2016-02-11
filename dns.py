#
# dns.py - Siimple DNS packet builder/parser
#
# Copyright (C) 2012 Mansour Behabadi <mansour@oxplot.com>
#

from __future__ import unicode_literals
from collections import deque
import struct

# String encodings and related stuff

try:
  range = xrange
except:
  pass

try:
  from cStringIO import StringIO as BytesIO
except ImportError:
  try:
    from StringIO import StringIO as BytesIO
  except ImportError:
    from io import BytesIO

try:
  maketrans = bytes.maketrans
except AttributeError:
  from string import maketrans

# ASCII only lowercase mapping

_lcasemap = maketrans(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                      b'abcdefghijklmnopqrstuvwxyz')

MAX_UDP_SIZE = 512

# Query/Response

M_QUERY = 0
M_RESPONSE = 1

# OPCODEs

OP_QUERY  = 0
OP_STATUS = 2

OPCODES = {OP_QUERY: 'QUERY', OP_STATUS: 'STATUS'}

# RCODEs

R_NONE    = 0
R_FORMAT  = 1
R_SERVER  = 2
R_NAME    = 3
R_NOTIMPL = 4
R_REFUSED = 5

RCODES = {R_NONE: 'NONE', R_FORMAT: 'FORMAT', R_SERVER: 'SERVER',
          R_NAME: 'NAME', R_NOTIMPL: 'NOTIMPL', R_REFUSED: 'REFUSED'}

# RR/Query types

T_A     = 1
T_NS    = 2
T_CNAME = 5
T_SOA   = 6
T_PTR   = 12
T_HINFO = 13
T_MX    = 15
T_TXT   = 16
T_AXFR  = 252
T_ANY   = 255

RRTYPES = {T_A: 'A', T_NS: 'NS', T_CNAME: 'CNAME', T_SOA: 'SOA',
           T_PTR: 'PTR', T_HINFO: 'HINFO', T_MX: 'MX', T_TXT: 'TXT'}
QTYPES = dict(RRTYPES)
QTYPES.update({T_AXFR: 'AXFR', T_ANY: 'ANY'})

# RR/Query classes

C_IN  = 1
C_CH  = 3
C_HS  = 4
C_ANY = 255

RRCLASSES = {C_IN: 'IN', C_CH: 'CH', C_HS: 'HS'}
QCLASSES = dict(RRCLASSES)
QCLASSES.update({C_ANY: 'ANY'})

class ParseError(Exception):
  pass

class RecursionError(ParseError):
  pass

class CorruptRRError(ParseError):
  pass

class NameTooLongError(ParseError):
  pass

class _Writer(object):
  __slots__ = ('stream', 'nlookup')
  def __init__(self, stream, nlookup = None):
    self.stream = stream
    self.nlookup = {} if nlookup is None else nlookup

class DomainName(object):

  @staticmethod
  def serialize(name, writer):

    name = tuple(name)
    if name == ():
      writer.stream.write(b'\0')
      return
    namelc = tuple(map(lambda i: i.translate(_lcasemap), name))
    I, i, nlookup = len(name), 0, writer.nlookup
    reloff = writer.stream.tell()
    while i < I:
      namelci_ = namelc[i:]
      lval = nlookup.get(namelci_)
      if lval is None:
        nlookup[namelci_] = reloff
      else:
        break
      reloff += len(namelc[i]) + 1
      i += 1
    if lval is None:
      postfix = b'\0'
    else:
      postfix = struct.pack(b'>H', 3 << 14 | lval)

    name = map(lambda i: struct.pack(b'B', len(i)) + i, name[:i])
    writer.stream.write(b''.join(name) + postfix)

  @staticmethod
  def deserialize(reader):
    tell, read, seek = reader.tell, reader.read, reader.seek
    seen = set((tell(),))
    finalname = deque(DomainName._deserialize_name(reader))
    savedoff = tell()
    while True:
      nextref = finalname.pop()
      if nextref is None:
        break
      if nextref in seen:
        raise RecursionError()
      seen.add(nextref)
      seek(nextref)
      finalname.extend(DomainName._deserialize_name(reader))
    seek(savedoff)
    length = sum(map(lambda i: len(i) + 1, finalname)) + 1
    if length > 255:
      raise NameTooLongError('Too long a domain name')
    return tuple(finalname)

  @staticmethod
  def _deserialize_name(reader):
    read, name = reader.read, deque()
    while True:
      l = ord(read(1))
      if l == 0:
        name.append(None)
        return name
      if l > 63:
        l2 = ord(read(1))
        name.append(((l & 0b111111) << 8) | l2)
        return name
      name.append(read(l))

class MessageHeader(object):

  SIZE = 12
  __slots__ = ('mtype', 'op', 'isauth', 'recdes', 'recavail', 'rcode',
    'qcount', 'anscount', 'authcount', 'adcount', 'trunc', 'id')
  def __init__(self, id = 0, mtype = 0, op = 0, isauth = False,
               recdes = False, recavail = False, rcode = 0, qcount = 0,
               anscount = 0, authcount = 0, adcount = 0, trunc = False):
    self.id = id
    self.mtype = mtype
    self.op = op
    self.isauth = isauth
    self.recdes = recdes
    self.recavail = recavail
    self.rcode = rcode
    self.qcount = qcount
    self.anscount = anscount
    self.authcount = authcount
    self.adcount = adcount
    self.trunc = trunc

  def serialize(self, writer):
    writer.stream.write(
      struct.pack(b'>6H', self.id,
        int(self.mtype) << 15 | int(self.op) << 11 |
        int(self.isauth) << 10 | int(self.trunc) << 9 |
        int(self.recdes) << 8  | int(self.recavail) << 7 |
        int(self.rcode),
        self.qcount, self.anscount, self.authcount, self.adcount)
    )

  @staticmethod
  def deserialize(reader):
    me = MessageHeader()
    head = reader.read(MessageHeader.SIZE)
    id, flags, qc, anc, nc, adc = struct.unpack(b'>6H', head)
    me.id = id
    me.mtype = (flags >> 15) & 1
    me.op = (flags >> 11) & 0b1111
    me.isauth = bool((flags >> 10) & 1)
    me.trunc = bool((flags >> 9) & 1)
    me.recdes = bool((flags >> 8) & 1)
    me.recavail = bool((flags >> 7) & 1)
    me.rcode = flags & 0b1111
    me.qcount = qc
    me.anscount = anc
    me.authcount = nc
    me.adcount = adc
    return me

class Message(object):
  __slots__ = ('header', 'questions', 'answers', 'auths', 'adds')
  def __init__(self, id = 0, mtype = 0, op = 0, isauth = False,
               recdes = False, recavail = False, rcode = 0,
               questions = [], answers = [], auths = [], adds = []):
    self.header = MessageHeader(id=id, mtype=mtype, op=op,
      isauth=isauth, recdes=recdes, recavail=recavail, rcode=rcode)
    self.questions = questions
    self.answers = answers
    self.auths = auths
    self.adds = adds

  def serialize(self, writer, isudp = True):

    self.header.qcount = len(self.questions)
    self.header.anscount = len(self.answers)
    self.header.authcount = len(self.auths)
    self.header.adcount = len(self.adds)

    writer = _Writer(stream=writer)
    startoff = writer.stream.tell()
    writer.stream.seek(MessageHeader.SIZE + startoff)

    for rarray in (self.questions, self.answers, self.auths, self.adds):
      for r in rarray:
        r.serialize(writer)

    if isudp and writer.stream.tell() > MAX_UDP_SIZE:
      self.header.trunc = True
      writer.stream.truncate(MAX_UDP_SIZE + startoff)
      writer.stream.seek(MAX_UDP_SIZE + startoff)

    endoff = writer.stream.tell()
    writer.stream.seek(startoff)
    self.header.serialize(writer)
    writer.stream.seek(endoff)

  @staticmethod
  def deserialize(reader):

    header = MessageHeader.deserialize(reader)
    ques, ans, auths, adds = [], [], [], []

    for i in range(header.qcount):
      ques.append(Question.deserialize(reader))
    for i in range(header.anscount):
      ans.append(RR.deserialize(reader))
    for i in range(header.authcount):
      auths.append(RR.deserialize(reader))
    for i in range(header.adcount):
      adds.append(RR.deserialize(reader))

    me = Message()
    me.header = header
    me.questions = ques
    me.answers = ans
    me.auths = auths
    me.adds = adds
    return me

class Question(object):
  __slots__ = ('type', 'cls', 'name')
  def __init__(self, type = 0, cls = 0, name = None):
    self.name = name
    self.type = type
    self.cls = cls

  def serialize(self, writer):
    DomainName.serialize(self.name, writer)
    writer.stream.write(struct.pack(b'>2H', self.type, self.cls))

  @staticmethod
  def deserialize(reader):
    me = Question()
    me.name = DomainName.deserialize(reader)
    fmt = b'>2H'
    me.type, me.cls = \
      struct.unpack(fmt, reader.read(struct.calcsize(fmt)))
    return me

class RR(object):
  __slots__ = ('name', 'type', 'cls', 'ttl')
  def __init__(self, name = None, type = 0, cls = 0, ttl = 0):
    self.name = name
    self.type = type
    self.cls = cls
    self.ttl = ttl

  def serialize(self, writer):
    stream = writer.stream
    write, tell, seek = stream.write, stream.tell, stream.seek

    DomainName.serialize(self.name, writer)

    fmt = b'>HHLH'
    fmt_len = struct.calcsize(fmt)
    savedoff = tell()
    seek(savedoff + fmt_len)
    self._rr_serialize(writer)

    endoff = tell()
    rr_len = endoff - savedoff - fmt_len
    seek(savedoff)
    write(struct.pack(fmt, self.type, self.cls, self.ttl, rr_len))
    seek(endoff)

  def _rr_serialize(self, writer):
    raise NotImplementedError('Must override in subclass')

  @staticmethod
  def deserialize(reader):
    name = DomainName.deserialize(reader)

    fmt = b'>HHLH'
    type, cls, ttl, rr_len = \
      struct.unpack(fmt, reader.read(struct.calcsize(fmt)))

    expected_endoff = reader.tell() + rr_len

    tmap = {T_A: RR_A, T_NS: RR_NS, T_CNAME: RR_CNAME, T_SOA: RR_SOA,
            T_PTR: RR_PTR, T_MX: RR_MX, T_TXT: RR_TXT}

    if type in tmap:
      me = tmap[type]._rr_deserialize(reader)
    else:
      reader.seek(expected_endoff)
      me = RR()

    if reader.tell() != expected_endoff:
      raise CorruptRRError('Corrupt RR data')

    me.name = name
    me.type = type
    me.cls = cls
    me.ttl = ttl

    return me

class RR_CNAME(RR):
  __slots__ = ('cname')
  def __init__(self, name = None, cls = 0, ttl = 0, cname = None):
    RR.__init__(self, name=name, type=T_CNAME, cls=cls, ttl=ttl)
    self.cname = cname

  def _rr_serialize(self, writer):
    DomainName.serialize(self.cname, writer)

  @staticmethod
  def _rr_deserialize(reader):
    return RR_CNAME(cname=DomainName.deserialize(reader))

class RR_MX(RR):
  __slots__ = ('exchange', 'pref')
  def __init__(self, name = None, cls = 0, ttl = 0, pref = 0,
               exchange = None):
    RR.__init__(self, name=name, type=T_MX, cls=cls, ttl=ttl)
    self.pref = pref
    self.exchange = exchange

  def _rr_serialize(self, writer):
    writer.stream.write(struct.pack(b'>H', self.pref))
    DomainName.serialize(self.exchange, writer)

  @staticmethod
  def _rr_deserialize(reader):
    me = RR_MX()
    ft = b'>H'
    (me.pref,) = struct.unpack(ft, reader.read(struct.calcsize(ft)))
    me.exchange = DomainName.deserialize(reader)
    return me

class RR_NS(RR):
  __slots__ = ('nsname')
  def __init__(self, name = None, cls = 0, ttl = 0, nsname = None):
    RR.__init__(self, name=name, type=T_NS, cls=cls, ttl=ttl)
    self.nsname = nsname

  def _rr_serialize(self, writer):
    DomainName.serialize(self.nsname, writer)

  @staticmethod
  def _rr_deserialize(reader):
    return RR_NS(nsname=DomainName.deserialize(reader))

class RR_PTR(RR):
  __slots__ = ('ptrname')
  def __init__(self, name = None, cls = 0, ttl = 0, ptrname = None):
    RR.__init__(self, name=name, type=T_PTR, cls=cls, ttl=ttl)
    self.ptrname = ptrname

  def _rr_serialize(self, writer):
    DomainName.serialize(self.ptrname, writer)

  @staticmethod
  def _rr_deserialize(reader):
    return RR_PTR(ptrname=DomainName.deserialize(reader))

class RR_SOA(RR):
  __slots__ = ('mname', 'rname', 'serial', 'refresh', 'retry', 'expire',
               'minimum')
  def __init__(self, name = None, cls = 0, ttl = 0, mname = None,
               rname = None, serial = 0, refresh = 0, retry = 0,
               expire = 0, minimum = 0):
    RR.__init__(self, name=name, type=T_SOA, cls=cls, ttl=ttl)
    self.mname = mname
    self.rname = rname
    self.serial = serial
    self.refresh = refresh
    self.retry = retry
    self.expire = expire
    self.minimum = minimum

  def _rr_serialize(self, writer):
    DomainName.serialize(self.mname, writer)
    DomainName.serialize(self.rname, writer)
    writer.stream.write(struct.pack(b'>5L', self.serial, self.refresh,
                        self.retry, self.expire, self.minimum))

  @staticmethod
  def _rr_deserialize(reader):
    me = RR_SOA()
    me.mname = DomainName.deserialize(reader)
    me.rname = DomainName.deserialize(reader)
    ft = b'>5L'
    me.serial, me.refresh, me.retry, me.expire, me.minimum = \
      struct.unpack(ft, reader.read(struct.calcsize(ft)))
    return me

class RR_TXT(RR):
  __slots__ = ('text')
  def __init__(self, name = None, cls = 0, ttl = 0, text = None):
    RR.__init__(self, name=name, type=T_TXT, cls=cls, ttl=ttl)
    self.text = text

  def _rr_serialize(self, writer):
    writer.stream.write(struct.pack(b'B', len(self.text)) + self.text)

  @staticmethod
  def _rr_deserialize(reader):
    l = ord(reader.read(1))
    return RR_TXT(text=reader.read(l))

class RR_A(RR):
  __slots__ = ('address')
  def __init__(self, name = None, cls = 0, ttl = 0, address = None):
    RR.__init__(self, name=name, type=T_A, cls=cls, ttl=ttl)
    self.address = address

  def _rr_serialize(self, writer):
    writer.stream.write(
      struct.pack(b'4B', *map(int, self.address.split(b'.'))))

  @staticmethod
  def _rr_deserialize(reader):
    return RR_A(
      address=('%d.%d.%d.%d' % struct.unpack(b'4B',
        reader.read(4))).encode('ascii')
    )
