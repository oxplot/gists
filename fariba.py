#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# fariba.py - a Farsi transcriber
#
# Copyright (C) 2008 Mansour Behabadi <mansour@oxplot.com>
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
#

#
# What is transcription?
#
# Transcription is the process of converting the sound of spoken words of a
# target language written using a certain script (in this case Latin script),
# to their corresponding written words using the script of the target
# language (in this case Farsi script).
#
# Here's an example:
#
# "afsaaneh" if read out loud sounds like a name in Farsi language which is
# written as "افسانه" in Farsi script. This transcriber given "afsaaneh" will
# produce "افسانه".
#
# Here are several examples that show the conventions and tips/tricks. On each
# line, to the left of "->" is the input and to the right of "->" is the
# output:
#
# salaam            ->  سلام
# aabaadaani        ->  آبادانی
# ttaavoos          ->  طاووس
# mecaal            ->  مثال
# ssa'aadat         ->  صعادت
# zzzzaaher         ->  ظاهر
# Orfe jaameEh      ->  عرف جامعه
# 'orfe jaame'eh    ->  عرف جامعه
# ghazaaleh         ->  غزاله
# mottma''en        ->  مطمئن
# soaal             ->  سوال
# moadab            ->  مودب
# iraan             ->  ایران
# ordoo             ->  اردو
# khaaahesh         ->  خواهش
# kheeesh           ->  خویش
# abo-l~fazzzl      ->  ابوالفضل
# be         ->  به
# to         ->  تو
# o          ->  و
# emrooz     ->  امروز
# oo         ->  او
# qom        ->  قم
# cho~n      ->  چون
# taqvaa~    ->  تقوی
# mi-aayad   ->  می‌آید
# hhat`aa~   ->  حَتّی
# hhatmann   ->  حتما
# k_oo       ->  كاو
# elaa~~heh  ->  الهه
# fat_hh     ->  فتح
# o~j        ->  اوج
# shaabdo~-l~'azzzzim -> شابدُ‌العَظیم
#
# If fariba is run on its own, it will transcribe the standard input to
# the standard output. You may use -d option to enable diacritics.
#
# Invokation example:
#
# $ echo faraanak | ./fariba.py
# ‎فرانک
#
# TODO provide some examples with diacritic option on
# TODO add support for more than two sets of mappings (with/out diacritics) to
#      allow different levels of diacriticcal details
#        - e.g. only KASREH and FATHA and ZAMMEH
# TODO add more punctuation support - e.g. double quotation marks
# TODO find a way to disinguish the pronunciation of 'beh' meaning 'behtar'
#      and 'beh', the adjoining word
# TODO add support for round brackets. it simple has to reverse them
# TODO treat "k_in" or "k_oo" is a special way so the correct pronunciation of
#      the word can be expressed in Farsi script with diacritics on

import sys

########################################################################
# Tokenizer
########################################################################

TokenType = {
    'word': {'name': 'word'},
    'nonword': {'name': 'nonword'},
    'number': {'name': 'number'},
    'punct': {'name': 'puncts'}
}

class Tokenizer:

    _wordchars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'`~"
    _numberchars = "0123456789"
    _punctchars = ",;?-[]_\""
    _allchars = _wordchars + _numberchars + _punctchars

    def __init__(self, stream):
        self._buffer = ''
        self._buffer_size = 1024
        self._curpos = 0
        self._backend = stream
        self._readahead = ''
    
    def __iter__(self):
        return self
    
    def next(self):

        token = self._readahead
        self._readahead = ''
        if not token:
            token = self.getnextchar()
            if not token:
                raise StopIteration()
        
        # determine the type of token
        if token in Tokenizer._wordchars:
            token = (TokenType['word'],
                     token + self.readword(Tokenizer._wordchars))
        
        elif token in Tokenizer._numberchars:
            token = (TokenType['number'],
                     token + self.readword(Tokenizer._numberchars))
        
        elif token in Tokenizer._punctchars:
            token = (TokenType['punct'], token)
        
        else:
            token = (TokenType['nonword'], token + self.readnonword())
        
        return token
    
    def readnonword(self):
        self._readahead = self.getnextchar()
        token = []
        while (self._readahead and
                not self._readahead in Tokenizer._allchars):
            token.append(self._readahead)
            self._readahead = self.getnextchar()
        return ''.join(token)
    
    def readword(self, chars):
        self._readahead = self.getnextchar()
        token = []
        while self._readahead and self._readahead in chars:
            token.append(self._readahead)
            self._readahead = self.getnextchar()
        return ''.join(token)
    
    def getnextchar(self):
        "Retrieves the next available character, "
        "or None if end of file is reached."
        
        if not self._buffer or self._curpos == len(self._buffer):
            self._buffer = self._backend.read(self._buffer_size)
            if not self._buffer:
                return None
            self._curpos = 0
        
        self._curpos += 1
        return self._buffer[self._curpos - 1]

###############################################################################
# Transcriber
###############################################################################

_digits = {
    '0': u'\u06F0',
    '1': u'\u06F1',
    '2': u'\u06F2',
    '3': u'\u06F3',
    '4': u'\u06F4',
    '5': u'\u06F5',
    '6': u'\u06F6',
    '7': u'\u06F7',
    '8': u'\u06F8',
    '9': u'\u06F9'
}

_puncts = {
    ';': u'\u061B',
    '?': u'\u061F',
    ',': u'\u060C',
    '-': u'\u200C',  # zero-width non-joiner
    '_': u''  # used to separate two word tokens without any character output
}

_start_form = {
    'aa': u'\u0622',
    'a': u'\u0627',
    'e': u'\u0627',
    'o': u'\u0627',
    'ee': u'\u0627\u06CC',
    'oo': u'\u0627\u0648',
    'i': u'\u0627\u06CC',
    'o~': u'\u0627\u0648',
}

_start_form_with_vowel = {
    'aa': u'\u0622',
    'a': u'\u0627\u064E',
    'e': u'\u0627\u0650',
    'o': u'\u0627\u064F',
    'ee': u'\u0627\u06CC',
    'oo': u'\u0627\u0648',
    'i': u'\u0627\u06CC',
    'o~': u'\u0627\u064F\u0648',
}

_end_form = {
    'o': u'\u0648',
    'ann': u'\u0627',
    'o~': u''
}

_end_form_with_vowel = {
    'o': u'\u064F\u0648',
    'ann': u'\u0627\u064B',
    'o~': u'\u064F'
}

_any_form = {
    'a': u'',
    'e': u'',
    'o': u'',
    'aa': u'\u0627',
    'b': u'\u0628',
    'p': u'\u067E',
    't': u'\u062A',
    'tt': u'\u0637',
    'T': u'\u0637',
    's': u'\u0633',
    'ss': u'\u0635',
    'S': u'\u0635',
    'c': u'\u062B',
    'sss': u'\u062B',
    'j': u'\u062C',
    'jj': u'\u0698',
    'J': u'\u0698',
    'ch': u'\u0686',
    'h': u'\u0647',
    'hh': u'\u062D',
    'H': u'\u062D',
    'kh': u'\u062E',
    'd': u'\u062F',
    'z': u'\u0632',
    'zz': u'\u0630',
    'Z': u'\u0630',
    'zzz': u'\u0636',
    'zzzz': u'\u0638',
    'r': u'\u0631',
    'sh': u'\u0634',
    "'": u'\u0639',
    "''": u'\u0626',
    "'''": u'\u0623', # should we show a normal ALEF in normal form?
    'q': u'\u0642',
    'f': u'\u0641',
    'gh': u'\u063A',
    'k': u'\u06A9',
    'g': u'\u06AF',
    'l': u'\u0644',
    'm': u'\u0645',
    'n': u'\u0646',
    'v': u'\u0648',
    'y': u'\u06CC',
    'i': u'\u06CC',
    'ee': u'\u06CC',
    'oo': u'\u0648',
    'oaa': u'\u0648\u0627',
    'oa': u'\u0648',
    'khaaa': u'\u062E\u0648\u0627',
    'kheee': u'\u062E\u0648\u06CC',
    'A': u'\u0639',
    'E': u'\u0639',
    'O': u'\u0639',
    'u': u'\u0639',
    '`': u'',
    'o~': u'\u0648',
    'aa~': u'\u06CC',
    'aa~~': u'',
    'l~': u'\u0627\u0644'
}

_any_form_with_vowel = {
    'a': u'\u064E',
    'e': u'\u0650',
    'o': u'\u064F',
    'aa': u'\u0627',
    'b': u'\u0628',
    'p': u'\u067E',
    't': u'\u062A',
    'tt': u'\u0637',
    'T': u'\u0637',
    's': u'\u0633',
    'ss': u'\u0635',
    'S': u'\u0635',
    'c': u'\u062B',
    'sss': u'\u062B',
    'j': u'\u062C',
    'jj': u'\u0698',
    'J': u'\u0698',
    'ch': u'\u0686',
    'h': u'\u0647',
    'hh': u'\u062D',
    'H': u'\u062D',
    'kh': u'\u062E',
    'd': u'\u062F',
    'z': u'\u0632',
    'zz': u'\u0630',
    'Z': u'\u0630',
    'zzz': u'\u0636',
    'zzzz': u'\u0638',
    'r': u'\u0631',
    'sh': u'\u0634',
    "'": u'\u0639',
    "''": u'\u0626',
    "'''": u'\u0623',
    'q': u'\u0642',
    'f': u'\u0641',
    'gh': u'\u063A',
    'k': u'\u06A9',
    'g': u'\u06AF',
    'l': u'\u0644',
    'm': u'\u0645',
    'n': u'\u0646',
    'v': u'\u0648',
    'y': u'\u06CC',
    'i': u'\u06CC',
    'ee': u'\u06CC',
    'oo': u'\u0648',
    'oaa': u'\u064F\u0648\u0670\u0627',
    'oa': u'\u064F\u0648\u0654\u064E',
    'khaaa': u'\u062E\u0648\u0670\u0627',
    'kheee': u'\u062E\u0648\u0652\u06CC', # TODO need a better diacritic here
    'A': u'\u0639\u064E',
    'E': u'\u0639\u0650',
    'O': u'\u0639\u064F',
    'u': u'\u0639',
    '`': u'\u0651',
    'o~': u'\u064F\u0648',
    'aa~': u'\u06CC\u0670',
    'aa~~': u'\u0670', # FIXME this causes letter before n after not to join
    'l~': u'\u0627\u0644'
}

_full_form = {}
_full_form['o'] = u'\u0648'

_full_form_with_vowel = {}
_full_form_with_vowel['o'] = u'\u0648'

_non_full_forms = [_start_form, _end_form, _any_form]

# sort keys based on length descending for all non full forms so longer
# sequences are matched first

_len_cmp = lambda x, y: -1 if len(x) < len(y) else \
    1 if len(x) > len(y) else 0
_start_form_keys = _start_form.keys()
_start_form_keys.sort(cmp = _len_cmp, reverse = True)

_end_form_keys = _end_form.keys()
_end_form_keys.sort(cmp = _len_cmp, reverse = True)

_any_form_keys = _any_form.keys()
_any_form_keys.sort(cmp = _len_cmp, reverse = True)


class Transcriber():

    def __init__(self, showvowel=False):
        self._any_form = _any_form_with_vowel if showvowel else _any_form
        self._start_form = _start_form_with_vowel if showvowel else _start_form
        self._end_form = _end_form_with_vowel if showvowel else _end_form
        self._full_form = _full_form_with_vowel if showvowel else _full_form

    def transcribe(self, token):
        "Transcribes token to Farsi script."
        tokentype, value = token
        if tokentype == TokenType['word']:
            return self.transword(value)
        elif tokentype == TokenType['number']:
            return u''.join([_digits[d] for d in value])
        elif tokentype == TokenType['punct']:
            return _puncts[value]
        elif tokentype == TokenType['nonword']:
            return value

    def transword(self, word):

        # whole word matching
        if word in _full_form.keys():
            return self._full_form[word]

        # partial
        transcribed = []
        curpos = 0
        while curpos < len(word):
            transletter = None
            
            # start forms
            if curpos == 0:
                for seq in _start_form_keys:
                    if word[curpos:curpos + len(seq)] == seq:
                        transletter = self._start_form[seq]
                        curpos += len(seq)
                        break

            # end forms
            if transletter == None:
                for seq in _end_form_keys:
                    if (word[curpos:curpos + len(seq)] == seq and
                        curpos + len(seq) == len(word)):
                        transletter = self._end_form[seq]
                        curpos += len(seq)
                        break
            
            # any form
            if transletter == None:
                for seq in _any_form_keys:
                    if word[curpos:curpos + len(seq)] == seq:
                        transletter = self._any_form[seq]
                        curpos += len(seq)
                        break

            if transletter != None:
                transcribed.append(transletter)
            else:
                curpos += 1
        
        return u''.join(transcribed)

###############################################################################
# Main program
#
# read standard input and send the transcription to the standard output
###############################################################################

if __name__ == '__main__':

    # using -v (vowel)
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        showvowel = True
    else:
        showvowel = False

    tokenizer = Tokenizer(sys.stdin)
    transcriber = Transcriber(showvowel = showvowel)
    override = False
    quote_open = False

    for token in tokenizer:
        ttype, tvalue = token
        if ttype != TokenType['nonword']:
            if tvalue == '[':
                override = True
            elif tvalue == ']':
                override = False
            elif not override:
                if tvalue == '"':
                    if quote_open:
                        sys.stdout.write(u"\xbb".encode('utf8'))
                        quote_open = False
                    else:
                        sys.stdout.write(u"\xab".encode('utf8'))
                        quote_open = True
                else:
                    sys.stdout.write(transcriber.transcribe(token)
                        .encode('utf8'))
            else:
                sys.stdout.write(tvalue.encode('latin1'))
        else:
            sys.stdout.write(tvalue.encode('latin1'))

