import re
from collections import defaultdict
from decimal import Decimal
from settle.util import Money, shorten

_receiver_re = re.compile('^([A-Za-z][-_A-Za-z0-9]*)(?:([%=*])([0-9.]+))?$')
_receivers_split_re = re.compile(',?[ \t\r\n]+')


class Payment:
    def __init__(self, group, giver, receivers, amount=None, currency=None, time=None, comment=None):
        self.group = group
        self.giver = giver
        if isinstance(receivers, str):
            self.receivers = Receivers.from_string(group, receivers)
        else:
            self.receivers = receivers
        self.amount = amount if amount is None else Decimal(amount)
        self.currency = currency or group.default_currency
        self.time = time
        self.comment = comment
        self._calculate_balances()

    def __repr__(self):
        return 'Payment(group=%r, giver=%r, receivers=%r, amount=%r, currency=%r, time=%r, comment=%r)' % (
            self.group, self.giver, self.receivers, self.amount, self.currency, self.time, shorten(self.comment, 50))

    def _calculate_balances(self):
        self.balances, amount = self.receivers.apply(self.amount, self.currency)
        self.balances.append((self.giver, Money(+amount, self.currency)))


class Receivers:
    def __init__(self, group, raw_receivers, modifier):
        self.group = group
        self.raw_receivers = tuple(raw_receivers)
        self.modifier = modifier

    @classmethod
    def from_string(cls, group, s):
        """
        Parse receivers string to `Receivers` object.
        """
        raw_receivers = []
        modifier = ()
        for r in _receivers_split_re.split(s):
            m = _receiver_re.match(r)
            if m is None:
                raise ValueError('Could not parse receiver information: %r' % r)
            name, mod_, value_ = m.groups()

            if mod_ is None:
                mod_ = '*'
                value = 1
            else:
                value = Decimal(value_)

            if modifier is ():
                modifier = mod_
            elif modifier != mod_:
                raise ValueError('Different receiver modifiers found')

            raw_receivers.append((name, value))

        if modifier == ():
            raise ValueError('No receivers given')

        return cls(group, raw_receivers, modifier)

    def apply(self, amount, currency=None):
        """
        Calculate balances for every receiver.

        amount may be None if absolute amounts are given for every receiver.
        currency may omitted when amount is of type `Money`.
        """

        balances = []

        if currency is None:
            if isinstance(amount, Money):
                amount = amount.value
                currency = amount.currency
            else:
                raise ValueError('Required argument currency not given')

        if self.modifier in ('*', '%') and amount is None:
            raise ValueError('Required field amount missing')

        # balanced (default. possibly with weight factors)
        if self.modifier == '*':
            sumfactors = sum(v for (n, v) in self.raw_receivers)

            for (name, value) in self.raw_receivers:
                val = amount * value / sumfactors
                balances.append((name, Money(-val, currency)))

        # fixed amounts given
        elif self.modifier == '=':
            sumamounts = 0

            for (name, value) in raw_receivers:
                balances.append((name, Money(-value, currency)))
                sumamounts += value

            if amount is None:
                amount = sumamounts
            else:
                if amount != sumamounts:
                    raise ValueError('Sum of amounts does not match the supplied payment amount')

        # manually defined shares
        elif modifier == '%':
            sumshares = sum(value for (_, _, value) in raw_receivers)

            if sumshares != 1:
                raise ValueError('Shares do not sum up to 1 (or 100%)')

            for (name, mod, share) in raw_receivers:
                balances.append((name, Money(-amount * share, currency)))

        else:
            raise RuntimeError('Invalid modifier. This should not have happened')

        return (balances, amount)


class Group:
    def __init__(self, default_currency):
        self.default_currency = default_currency
