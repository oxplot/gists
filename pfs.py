#!/usr/bin/env python
# vim: ts=2:sw=2:tw=72:expandtab:sts=2
#
# pfs.py - Pretty Fucking Simple static blog generator
# Copyright (C) 2013 Mansour Behabadi <mansour@oxplot.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Pretty Fucking Simple static blog generator."""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

__author__ = 'Mansour Behabadi'
__copyright__ = 'Copyright (C) 2013 Mansour Behabadi'
__credits__ = ['Mansour Behabadi']
__email__ = 'mansour@oxplot.com'
__license__ = 'GPLv3'
__maintainer__ = 'Mansour Behabadi'
__version__ = '1.0'
__progname__ = 'pfs'

_WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
          'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

from subprocess import Popen, PIPE
import argparse
import calendar
import functools
import markdown
import os
import re
import shutil
import sys
import time

try:
  unicode = unicode
except NameError:
  unicode = str

try:
  xrange = xrange
except NameError:
  xrange = range

try:
  from StringIO import StringIO
except ImportError:
  from io import StringIO

def _date_to_utcts(ts):
  return calendar.timegm(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))

def _fmt_ts(ts, fmt = '%(wday_name)s, %(mday)d %(mon_name)s'
                      ' %(yr)d %(hr)02d:%(m)02d:%(s)02d GMT'):
  if type(ts) not in (int, float):
    ts = _date_to_utcts(ts)
  ts = time.gmtime(ts)
  yr, mon, mday, hr, m, s, wday, yday, isdst = ts
  return fmt % {'yr': yr, 'mon': mon, 'mday': mday, 'hr': hr, 'm': m,
                's': s, 'wday': wday, 'yday': yday,
                'wday_name': _WEEKDAYS[wday],
                'mon_name': _MONTHS[mon - 1]}

def _xml_escape(text):
  return re.sub(r'(["\'<>&])', lambda m: '&%s;' % {
    '"': 'quot', "'": 'apos', '<': 'lt', '>': 'gt', '&': 'amp'
  }[m.group(1)], text)

class PFSError(Exception):
  pass

class PFS(object):
  """Static blog generator."""

  def __init__(self, cfg, opts):
    self.cfg = cfg
    self.opts = opts
    if 'output' not in cfg and opts.output is None:
      raise PFSError('output directory is not defined anywhere')
    self._outdir = opts.output or cfg.output
    self._page_meta = {}

  def _ind(self, path):
    return os.path.join(self.opts.root, path)

  def _outd(self, path):
    return os.path.join(self._outdir, path)

  def _mainroll_outter(self, pagenum, content):
    if pagenum == 1:
      destdir = self._outdir
    else:
      destdir = self._outd(str(pagenum))
      os.makedirs(destdir)
    path = os.path.join(destdir, 'index.html')
    open(path, 'wb').write(content.encode('utf8'))

  def _rssroll_outter(self, pagenum, content):
    if pagenum > 1:
      return
    open(self._outd(self.cfg.get('rss_file', 'rss.xml')),
      'wb').write(content.encode('utf8'))

  def _load_bunprocs(self, loc):
    procs = []
    rt = self._ind(loc)
    if os.path.exists(rt):
      for f in sorted(os.listdir(rt)):
        if self._ignorepat and self._ignorepat.search(f):
          continue
        raw = open(os.path.join(rt, f), 'rb').read().decode('utf8')
        lines = re.sub(r'\r\|\r|\n', '\n', raw.strip()).split('\n')
        code = 'from __future__ import unicode_literals\n'
        code += 'def process(text):\n'
        code += '\n'.join(map(lambda x: ' ' + x, lines))
        procs.append(compile(code, '<string>', 'exec'))
    return procs

  def build(self):
    if not os.path.exists(self._outdir):
      raise PFSError('destination directory does not exist')
    if os.listdir(self._outdir):
      raise PFSError('destination directory is not empty')
    self._ignorepat = re.compile(self.cfg.get('ignore', r'[\x00]\A'))
    self._pre_procs = self._load_bunprocs('preprocs')
    self._post_procs = self._load_bunprocs('postprocs')
    self._pages_list = self._build_pages('pages', 'page.html')
    self._posts_list = self._build_pages('posts', 'post.html')
    self._build_rolls(
      tpl='roll.html',
      ppp=int(self.cfg['posts_per_page']),
      outter=self._mainroll_outter
    )
    self._build_rolls(
      tpl='rss.xml',
      ppp=int(self.cfg.get('rss_count', self.cfg['posts_per_page'])),
      outter=self._rssroll_outter,
      depth_override=0,
      force_abs=True
    )
    self._build_media()
    self._build_redirects()
    self._build_misc()

  def _build_misc(self):
    for misc_tpl in self.cfg.get('misc', []):
      src, dst = map(lambda x: x.replace('/', os.path.sep).strip(),
                     misc_tpl.split('->'))
      dst_dir, dst_file = os.path.split(dst)
      tpl = CSTE(self._tplldr, src)
      var = self._populate_var(depth=dst.count('/'))
      if dst_dir and not os.path.exists(self._outd(dst_dir)):
        os.makedirs(self._outd(dst_dir))
      open(self._outd(dst), 'wb').write(tpl.gen(**var).encode('utf8'))

  def _build_redirects(self):
    redirtpl = CSTE(self._tplldr, 'redirect.html')
    for redir in self.cfg.get('redirects', []):
      frm, to = map(unicode.strip, redir.split('->'))
      frm_dir, frm_file = os.path.split(frm.replace('/', os.path.sep))
      depth = frm.count('/')
      hdr = self._load_page(
        self._page_meta[to]['_filepath'],
        depth=depth
      )[0]
      var = self._populate_var(hdr=hdr, depth=depth)
      output = redirtpl.gen(**var)
      if frm_dir and not os.path.exists(self._outd(frm_dir)):
        os.makedirs(self._outd(frm_dir))
      open(self._outd(frm), 'wb').write(output.encode('utf8'))

  def _build_media(self):
    shutil.copytree(self._ind('media'), self._outd('media'))

  def _build_rolls(self, tpl, ppp, outter, depth_override = None,
                   force_abs = False):
    genedtpl = CSTE(self._tplldr, tpl)
    plist = list(self._posts_list)
    plist.sort(
      key=lambda x: self._page_meta[x]['published'],
      reverse=True
    )
    pnum = 1
    for start in xrange(0, len(plist), ppp):
      if depth_override is None:
        depth = 0 if start == 0 else 1
      else:
        depth = depth_override
      var = self._populate_var(depth=depth, force_abs=force_abs)
      var['posts'] = [
        self._load_page(self._page_meta[x]['_filepath'],
                        depth=depth, force_abs=force_abs)
        for x in plist[start:start + ppp]
      ]
      var['cur_page_num'] = (start // ppp) + 1
      var['prev_page_num'] = (start // ppp) if start >= ppp else None
      var['next_page_num'] = (start // ppp) + 2 \
        if start + ppp < len(plist) else None
      output = genedtpl.gen(**var)
      outter(var['cur_page_num'], output)

  def _populate_var(self, hdr = {}, depth = None, force_abs = False):
    depth = hdr['slug'].count('/') + 1 if depth is None else depth
    var = {}
    var.update(self.cfg)
    var.update(hdr)
    var['CFG'] = dict(self.cfg)
    def doproc(text):
      return self._process(text)
    def abs_link(path):
      return var['blog_url'].rstrip('/') + '/' + path
    def root_link(path):
      return abs_link(path) if force_abs else '../' * depth + path
    def media_link(path):
      return root_link('media/' + path)
    def page_link(slug):
      return root_link(slug + '/')
    def roll_link(pagenum):
      return root_link('' if pagenum == 1 else str(pagenum) + '/')
    var['doproc'] = doproc
    var['root_link'] = root_link
    var['media_link'] = media_link
    var['page_link'] = page_link
    var['roll_link'] = roll_link
    var['abs_link'] = abs_link
    var['utc_stamp'] = _date_to_utcts
    var['fmt_stamp'] = _fmt_ts
    var['generator'] = {
      'name': __progname__,
      'ver': __version__
    }
    return var

  def _build_pages(self, inpdir, tpl):
    genedtpl = CSTE(self._tplldr, tpl)
    pagelist = []
    for path, dirs, files in os.walk(self._ind(inpdir)):
      for f in files:
        if self._ignorepat and self._ignorepat.search(f):
          continue
        hdr, body = self._load_page(os.path.join(path, f))
        if hdr.get('hidden', 'false') == 'true':
          continue
        hdr['_file_path'] = os.path.join(path, f)
        destdir = self._outd(hdr['slug'].replace('/', os.path.sep))
        os.makedirs(destdir)
        var = self._populate_var(hdr=hdr)
        var['body_content'] = body
        output = genedtpl.gen(**var)
        open(os.path.join(destdir, 'index.html'),
             'wb').write(output.encode('utf8'))
        pagelist.append(hdr['slug'])
    return pagelist

  def _tplldr(self, name):
    if name.startswith('!@#'):
      return name[3:]
    if name.startswith(os.path.sep):
      path = self._ind(name.lstrip(os.path.sep))
    else:
      path = os.path.join(self._ind('templates'), name)
    return open(path, 'rb').read().decode('utf8')

  def _load_page(self, path, depth = None, force_abs = False):
    data = open(path, 'rb').read().decode('utf8')
    data = re.sub(r'\r\n|[\r\n]', '\n', data)
    secs = data.split('\n\n', 1)
    if len(secs) < 2:
      raise PFSError("'%s' is missing header" % path)
    header, body = sssd_load(secs[0]), secs[1]
    var = self._populate_var(
      hdr=header, depth=depth, force_abs=force_abs)
    body = CSTE(self._tplldr, '!@#' + body).gen(**var)
    body = self._process(body)
    bodysecs = body.split('<!--BREAK-->')
    header['_filepath'] = path
    self._page_meta[header['slug']] = header
    return (header, bodysecs)

  def _post_process(self, text):
    return self._bun_process(self._post_procs, text)

  def _pre_process(self, text):
    return self._bun_process(self._pre_procs, text)

  def _bun_process(self, procs, text):
    for compiled in procs:
      localvars = {}
      exec(compiled, {}, localvars)
      text = localvars['process'](text)
    return text

  def _process(self, text):
    return self._post_process(markdown.markdown(
      self._pre_process(text),
      output_format='html5',
      extensions=['abbr', 'footnotes']
    ))

class CSTE(object):
  """Considerably Simple Template Engine."""

  def __init__(self, loader, tplname):
    self._inblock = False
    self._extends = None
    self._included = {}
    self._lastpos = 0
    self._stack = []
    self._indent = 0
    self._lines = []
    self.loader = loader
    self.tpl = loader(tplname)
    self._build()

  def _expr(self, match):
    """Handle different template expressions."""

    if not self._extends or self._inblock:
      self._write('_writer.write(%r)'
                  % self.tpl[self._lastpos:match.start()])
    self._lastpos = match.end()

    stmt, stmtdet, var = map(
      lambda x: '' if x is None else x.strip(), match.groups())

    if var:
      self._write('_writer.write(_escape(unicode(%s)))' % var)

    elif stmt == 'extends':
      self._extends = CSTE(self.loader, stmtdet)

    elif stmt == 'block':
      self._stack.append(('block', stmtdet))
      self._inblock = True
      if self._extends:
        self._write('if True:')
        self._indent += 1
        self._write('_writer = StringIO()')
      else:
        self._write('if %r in _blocks:' % stmtdet)
        self._indent += 1
        self._write('_writer.write(_blocks[%r])' % stmtdet)
        self._indent -= 1
        self._write('else:')
        self._indent += 1

    elif stmt in ('for', 'if', 'while'):
      self._stack.append((stmt, stmtdet))
      self._write('%s %s:' % (stmt, stmtdet))
      self._indent += 1

    elif stmt == 'elif':
      self._indent -= 1
      self._write('%s %s:' % (stmt, stmtdet))
      self._indent += 1

    elif stmt == 'else':
      self._indent -= 1
      self._write('%s:' % stmt)
      self._indent += 1

    elif stmt == 'set':
      assignee, val = re.match(
        '([a-zA-Z][a-zA-Z0-9_]*)\s*=\s*(.+)', stmtdet).groups()
      self._write('%s = %s' % (assignee, val))

    elif stmt == 'include':
      if stmtdet not in self._included:
        self._included[stmtdet] = CSTE(self.loader, stmtdet)
      self._write('_writer.write(_include(%r))' % stmtdet)

    elif stmt in ('import', 'from'):
      self._write('%s %s' % (stmt, stmtdet))

    elif stmt == 'raw':
      self._write('_writer.write(%s)' % stmtdet)

    elif stmt == 'escape':
      self._write('_writer.write(xml_escape(%s))' % stmtdet)

    elif stmt == 'autoescape':
      self._write('_escape = ' 
        + ('_no_escape' if stmtdet == 'None' else stmtdet))

    elif stmt == 'apply':
      self._stack.append((stmt, stmtdet))
      self._write('if True:')
      self._indent += 1
      self._write('_writers.append(_writer)')
      self._write('_writer = StringIO()')

    elif stmt == 'end':
      tag, dets = self._stack.pop()
      if tag == 'block':
        self._inblock = False
        if self._extends:
          self._write('_myblocks[%r] = _writer.getvalue()' % dets)
      elif tag == 'apply':
        self._write('_interm = _writer.getvalue()')
        self._write('_writer = _writers.pop()')
        self._write('_writer.write(%s(_interm))' % dets)
      self._indent -= 1

    return ''

  def _build(self):
    """Compile the template into python code object."""

    self._write('from __future__ import unicode_literals')
    self._write('def _gen(_blocks={}):')
    self._indent += 1
    self._write('_escape = xml_escape')
    self._write('_myblocks = {}')
    self._write('_writers = []')
    self._write('_writer = StringIO()')

    re.sub(r'[{]%\s*([a-z]+)\s+(.*?)\s*%[}]|[{][{]\s*(.*?)\s*[}][}]',
           self._expr, self.tpl)

    if self._extends:
      self._write('_myblocks.update(_blocks)')
      self._write('return _myblocks')
    else:
      self._write('_writer.write(%r)'
                  % self.tpl[self._lastpos:])
      self._write('return _writer.getvalue()')

    self._code = compile('\n'.join(self._lines), '<string>', 'exec')

  def _write(self, line):
    """Write into code buffer with current indentation."""
    self._lines.append(' ' * self._indent + line)

  def _include(self, _blocks, var, tplname):
    return self._included[tplname].gen(_blocks=_blocks, **var)

  def gen(self, _blocks = {}, **var):
    """Generate the processed template.

    _blocks -- map of block names to block content
    var -- variables/functions to be used in the template

    """

    globalvars = {
      'StringIO': StringIO,
      'unicode': unicode,
      '_include': functools.partial(self._include, _blocks, var),
      'xml_escape': _xml_escape,
      '_no_escape': lambda x: x,
    }
    globalvars.update(var)
    localvars = {}
    exec(self._code, globalvars, localvars)
    _gen = localvars['_gen']

    if self._extends:
      return self._extends.gen(_blocks=_gen(_blocks=_blocks), **var)
    else:
      return _gen(_blocks=_blocks)

def sssd_load(data):
  """Load a Stupidly Simple Structured Data."""
  lines = list(map(unicode.rstrip,
    re.sub(r'(\r\n|[\r\n])', '\n', data).strip().split('\n')))
  root = ({}, [])
  stack = [root]
  while lines:
    m = re.search(
      r'^((?:  )*)([a-zA-Z_][a-zA-Z_0-9]*:|-) *(\'.*\'|.*)$',
      lines.pop(0)
    )
    if not m:
      continue
    lev, key, val = len(m.group(1)) // 2, m.group(2), m.group(3)
    stack = stack[:lev + 1]
    if val:
      val = val[1:-1] if val.startswith("'") else val
      if key == '-': stack[-1][1].append(val)
      else: stack[-1][0][key[:-1]] = val
    else:
      newbranch = ({}, [])
      if key == '-': stack[-1][1].append(newbranch)
      else: stack[-1][0][key[:-1]] = newbranch
      stack.append(newbranch)
  def _get_pop(node):
    if type(node) == tuple:
      if node[0]:
        return dict((k, _get_pop(node[0][k])) for k in node[0])
      else:
        return list(map(_get_pop, node[1]))
    else:
      return node
  return _get_pop(root)

def sssd_dump(data, lev = 0):
  """Dump a Stupidly Simple Structured Data."""
  lines = []
  if type(data) == dict:
    for k in data:
      if type(data[k]) in (dict, list):
        lines.append(' ' * (lev * 2) + k + ':')
        lines.extend(sssd_dump(data[k], lev + 1))
      else:
        lines.append(' ' * (lev * 2) + k + ': '
                     + sssd_dump(data[k], lev))
  elif type(data) == list:
    for i in data:
      if type(i) in (dict, list):
        lines.append(' ' * (lev * 2) + '-')
        lines.extend(sssd_dump(i, lev + 1))
      else:
        lines.append(' ' * (lev * 2) + '- ' + sssd_dump(i, lev))
  else:
    val = "'%s'" % data if not data or data.strip() != data else data
    return val

  return lines if lev > 0 else '\n'.join(lines)

def main():
  """Parse command line arguments."""

  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description='Pretty Fucking Simple static blog generator'
  )
  parser.add_argument(
    '-c', '--config',
    default=None,
    metavar='FILE',
    help='path to config file - default is <root>/config'
  )
  parser.add_argument(
    '-r', '--root',
    default='.',
    metavar='DIR',
    help="path to root of the blog - default is '.'"
  )
  subparsers = parser.add_subparsers(
    title='main commands',
    dest='cmd'
  )

  parser_a = subparsers.add_parser(
    'build',
    help='build the static blog content'
  )
  parser_a.add_argument(
    '-o', '--output',
    default=None,
    metavar='DIR',
    help='path to output directory - default as defined in config'
  )

  opts = parser.parse_args()

  # Load the config

  cfgpath = opts.config or os.path.join(opts.root, 'config')
  cfg = sssd_load(open(cfgpath, 'rb').read().decode('utf8'))

  try:
    pfsinst = PFS(cfg, opts)
    if opts.cmd == 'build':
      pfsinst.build()
  except PFSError as e:
    print('%s: error: %s' % (__progname__, e.args[0]), file=sys.stderr)
    exit(1)

if __name__ == '__main__':
  main()
