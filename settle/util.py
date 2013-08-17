# -*- coding: utf-8 -*-
import os
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

def debug(str):
    if os.environ.get('SETTLE_DEBUG') == '1':
        print(str, file=sys.stderr)

def format_decimal(n):
    return '%+.2f' % n
