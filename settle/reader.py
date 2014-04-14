#!/usr/bin/env python3
# -*- coding: utf8 -*-
import os
import re
import sys
from collections import namedtuple
from dateutil.parser import parse as parse_date
from settle import FILE_CHARSET
from settle.payment import Payment
from settle.util import lowercase_keys, debug, generate_random_filename, format_datetime, sort_payment_keys

_confline_re = re.compile(r'^(?P<k>[^\s:]+)\s*:\s*(?P<v>.*)$')
_key_re = re.compile(r'^[^\s:]+$')
KVPair = namedtuple('KVPair', ['k', 'v'])


def read_payment(f, group):
    d = read_file(f)
    d = lowercase_keys(d)
    args = {}

    if d == {}:
        raise ReaderValueError('File is empty: %r' % f)

    for k, v in d.items():
        if k in ('giver', 'receivers', 'amount', 'currency', 'comment'):
            if k in args:
                raise ReaderValueError('Duplicate field %s' % k)
            args[k] = v
        elif k == 'date':
            args[k] = parse_date(v)
        else:
            raise ReaderValueError('Unkown field name: %r' % k)

    for field in 'giver', 'receivers':
        if field not in d:
            raise ReaderValueError('Required field %s missing (file %r)' % (field, f))
    # don't check amount here because it is optional with per-recipient amounts

    return Payment(group, **args)


def read_all_payments(group):
    for f in find_payment_files(group):
        debug('payment found: %s' % f)
        yield read_payment(f, group)


def find_payment_files(group):
    dir = group.path('payments')
    debug('searching for payments in %s' % dir)
    for f_ in os.listdir(dir):
        f = os.path.join(dir, f_)
        if f_[0] != '.' and os.path.isfile(f):
            yield f
        else:
            debug('skip %s' % f)


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

_read_file_no_default = object()
def read_file(filename, default=_read_file_no_default):
    """
    Like `read()` but must be given a filename.

    If file does not exist and default is given, return that.
    Else and on all other kinds of io errors, raise them as usual.
    """
    try:
        f = open(filename, encoding=FILE_CHARSET)
    except IOError as e:
        if e.errno == 2 and default is not _read_file_no_default:
            return default
        raise

    try:
        return read(f)
    finally:
        f.close()

class ReaderError(Exception):
    pass

class ReaderParseError(ReaderError):
    pass

class ReaderDuplicateEntryError(ReaderError):
    pass

class ReaderValueError(ReaderError):
    pass

def store_payment(payment, filename=None):
    """
    Store the Payment to disk as a new file.

    If no filename is given, generate a random one.

    N.B: This is not race condition safe for python < 3.3.
    """
    if filename is not None:
        path = payment.group.path('payments', filename)
        if os.path.exists(path):
            raise ValueError('File already exists: %r' % path)

    while filename is None:
        filename = generate_random_filename(
            format_datetime(payment.date, date_only=True),
            payment.giver)
        debug(filename)
        path = payment.group.path('payments', filename)

        if os.path.exists(path):
            filename = None

    mode = 'w' if sys.version_info < (3,3) else 'wx'

    with open(path, mode, encoding=FILE_CHARSET) as f:
        write(f, payment.serialize())

def write(f, data):
    for k in sort_payment_keys(data):
        if not _key_re.match(k):
            raise WriterKeyValueError('Invalid characters in key: %r' % k)

        if data[k] is None:
            continue

        if '\n' in str(data[k]):
            f.write('%s:\n    %s\n' % (k, data[k].replace('\n', '\n    ')))
        else:
            f.write('%s: %s\n' % (k, data[k]))
    f.flush()

class WriterError(Exception):
    pass

class WriterKeyValueError(WriterError):
    pass

if __name__ == '__main__':
    import pprint, sys
    pprint.pprint(parseconfig(sys.stdin))
