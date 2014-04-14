# -*- coding: utf-8 -*-
import os
import random
import re
import string
import sys
from decimal import Decimal

def shorten(s, length, allow_none=True):
    if s is None and allow_none:
        return ''
    if len(s) <= length:
        return s
    else:
        return s[:length-4] + ' ...'

def lowercase_keys(d):
    """Return a copy of dictionary `d` with keys lowercased"""
    return {k.lower(): v for k, v in d.items()}

class Money:
    """Stores an amount of money with currency"""
    def __init__(self, value, currency):
        self.value = value
        self.currency = currency

    def __repr__(self):
        return 'Money(%r, %r)' % (self.value, self.currency)

    def __str__(self):
        return '%s %s' % (format_decimal(self.value), self.currency)

    @classmethod
    def zero(cls, currency):
        def zero_():
            return Money(0, currency)
        return zero_

    def __eq__(self, other):
        return self.currency == other.currency and self.value == other.value

    def __add__(self, other):
        if self.currency != other.currency:
            raise ValueError('Cannot add different currencies: %r and %r'
                             % (self.currency, other.currency))
        return Money(self.value + other.value, self.currency)

    def __sub__(self, other):
        if self.currency != other.currency:
            raise ValueError('Cannot subtract different currencies: %r and %r'
                             % (self.currency, other.currency))
        return Money(self.value - other.value, self.currency)

    def __neg__(self):
        return Money(-self.value, self.currency)

    def __pos__(self):
        return Money(+self.value, self.currency)

    def __abs__(self):
        return Money(abs(self.value), self.currency)

def debug(str):
    if os.environ.get('SETTLE_DEBUG') == '1':
        print(str, file=sys.stderr)

def format_decimal(n, sign=True):
    return ('%+ 7.2f' if sign else '% 7.2f') % n

def is_list(s):
    return s.startswith('%')

def ask(question, long=None, require=None, blank=False, forbidden=None,
        default=None,
        forbidden_msg='Not allowed. Please enter something else.'):
    if isinstance(forbidden, str):
        forbidden = re.compile(forbidden)
    def check_forbidden(s):
        if forbidden is None:
            return True
        if hasattr(forbidden, 'search'):
            if forbidden.search(s):
                print('>', forbidden_msg, file=sys.stderr)
                return False
        elif hasattr(forbidden, '__call__'):
            msg = forbidden(s)
            if msg:
                print(msg, file=sys.stderr)
                return False
        elif s in forbidden:
            print(forbidden_msg, file=sys.stderr)
            return False
        return True

    if isinstance(require, str):
        require = re.compile(require)

    if default:
        prompt = '%s[%s] ' % (question, default)
    else:
        prompt = question if not long else question + '(enter for help) '
    r = input(prompt)

    for i in range(15):
        if require and require.search(r):
            if check_forbidden(r):
                return r
        if not require and r:
            if check_forbidden(r):
                return r

        if blank and r == '':
            return r
        if default and r == '':
            return default
        r = input(long if long else question)

    raise ValueError('Asked too often, giving up.')

def generate_random_filename(*prefixes, randlength=8, join='_'):
    """
    Generate a random filename, consisting of all non-empty prefixes and a
    random string of length `randlength`[8] joined by `join`[_].

    N.B.: Sanity of given strings is not checked by this function.
    """
    prefixes = list(prefixes)
    prefixes.append(''.join(random.choice(string.ascii_lowercase + string.digits)
                            for x in range(randlength)))
    return join.join(filter(None, prefixes))

def format_datetime(dt, date_only=False):
    """
    Format a datetime object in the shortest manner possible, that is
    only show date if time is midnight, omit second if it zero.
    If `date_only`=True, only show the date in any case.
    """
    if dt is None:
        return ''
    elif date_only or dt.hour == dt.minute == dt.second == 0:
        return dt.strftime('%Y-%m-%d')
    elif dt.second == 0:
        return dt.strftime('%Y-%m-%d %H:%M')
    else:
        return dt.strftime('%Y-%m-%d %H:%M:%S')

_payment_keys_order = ['giver', 'receivers', 'amount', 'currency', 'date', 'comment']
def sort_payment_keys(keys):
    """
    Sort the given list in the most natural order of the keys of a payment object.
    """
    def genkey(k):
        if k in _payment_keys_order:
            return (_payment_keys_order.index(k), None)
        else:
            return (len(_payment_keys_order), k)

    return sorted(keys, key=genkey)
