# -*- coding: utf-8 -*-
import os
import re
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

def format_decimal(n):
    return '%+.2f' % n

def is_list(s):
    return s.startswith('%')

def ask(question, long=None, require=None, blank=False, forbidden=None,
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
        require = re.compile(str)

    r = input(question if not long else question + '(enter for help) ')
    for i in range(15):
        if require and require.search(r):
            if check_forbidden(r):
                return r
        if not require and r:
            if check_forbidden(r):
                return r

        r = input(long if long else question)
        if blank and r == '':
            return r

    raise ValueError('Asked too often, giving up.')
