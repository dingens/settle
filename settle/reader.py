#!/usr/bin/python3
# -*- coding: utf8 -*-
import re
from collections import namedtuple
from settle.payment import Payment
from settle.util import lowercase_keys

_confline_re = re.compile(r'^(?P<k>[^\s]+)\s*:\s*(?P<v>.*)$')
KVPair = namedtuple('KVPair', ['k', 'v'])


def read_payment(f, group):
    d = read(f)
    d = lowercase_keys(d)
    args = {}

    for k, v in d.items():
        if k in ('giver', 'receivers', 'amount', 'currency', 'time', 'comment'):
            if k in args:
                raise ReaderValueError('Duplicate field %s' % k)
            args[k] = v
        else:
            raise ReaderValueError('Unkown field name: %r in %r' % (k, d))

    for f in 'giver', 'receivers':
        if f not in d:
            raise ReaderValueError('Required field %s missing' % f)
    # don't check amount because it is optional with per-recipient amounts

    return Payment(group, **args)


def read(f):
    d = {}
    last = None
    lno = 0

    def set(k, v):
        if k in d:
            raise ReaderDuplicateEntryError('Key %r already present at '
                                            'line %d: %r' % (k, lno, line))
        d[k] = v

    for line in f:
        lno += 1

        if line[0] == '#':
            continue
        if last:
            if line[0] in ' \t':
                last.v.append(line.lstrip(' \t'))
                continue
            else:
                set(last.k, ''.join(last.v))
                last = None

        if line.strip() == '':
            continue

        m = _confline_re.match(line)
        if m is None:
            if line[0] in ' \t':
                raise ReaderParseError('Continuation only allowed with empty '
                      'first line at line %d: %r' % (lno, line))
            raise ReaderParseError('Could not parse line %d: %r' % (lno, line))

        k, v = m.groups()
        if v == '':
            last = KVPair(k, [])
        else:
            set(k, v)

    if last:
        set(last.k, ''.join(last.v))

    return d

class ReaderError(Exception):
    pass

class ReaderParseError(ReaderError):
    pass

class ReaderDuplicateEntryError(ReaderError):
    pass

class ReaderValueError(ReaderError):
    pass

if __name__ == '__main__':
    import pprint, sys
    pprint.pprint(parseconfig(sys.stdin))
