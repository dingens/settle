import re
from collections import defaultdict
from decimal import Decimal
from settle.util import debug, is_list, Money, shorten

_receiver_re = re.compile('^(%?[A-Za-z][-_A-Za-z0-9]*)(?:([%=*])([0-9.]+))?$')
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
        from settle import MAX_LIST_RESOLVER_RECURSION_DEPTH

        self.balances = []
        raw_balances, self.amount = self.receivers.apply(self.amount, self.currency)

        i = MAX_LIST_RESOLVER_RECURSION_DEPTH
        while raw_balances:
            new_raw_balances = []

            debug('raw: %r' % raw_balances)
            for name, val in raw_balances:
                if is_list(name):
                    bal, _amount = self.group.lists[name[1:]].apply(-val)
                    new_raw_balances.extend(bal)
                else:
                    self.balances.append((name, val))
            raw_balances = new_raw_balances
            i -= 1

            if i <= 0:
                raise RuntimeError('Maximum list resolver recursion depth reached. Maybe there is a loop?')

        self.balances.append((self.giver, Money(+self.amount, self.currency)))


class Receivers:
    def __init__(self, group, raw_receivers, modifier):
        self.group = group
        self.raw_receivers = tuple(raw_receivers)
        self.modifier = modifier

    @classmethod
    def from_string(cls, group, s, is_list=False):
        """
        Parse receivers string to `Receivers` object.

        If `is_list` is True, don't allow the `=` (fixed per-receiver amount) modifier.
        """
        raw_receivers = []
        modifier = ()
        for r in _receivers_split_re.split(s):
            if not r:
                continue

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

        if is_list and modifier == '=':
            raise ValueError("'=' modifier not allowed in group definitions")

        return cls(group, raw_receivers, modifier)

    def apply(self, amount, currency=None):
        """
        Calculate balances for every receiver.

        amount may be None if absolute amounts are given for every receiver.
        currency may be omitted when amount is of type `Money`.
        """

        balances = []

        if currency is None:
            if isinstance(amount, Money):
                currency = amount.currency
                amount = amount.value
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

        # fixed per-receiver amounts given
        elif self.modifier == '=':
            sumamounts = 0

            for (name, value) in raw_receivers:
                balances.append((name, Money(-value, currency)))
                sumamounts += value

            if amount is None:
                # no total amount given, calculate it
                amount = sumamounts
            else:
                # total amount given voluntarily, compare
                if amount != sumamounts:
                    raise ValueError('Sum of amounts does not match the supplied payment amount')

        # manually defined shares
        elif modifier == '%':
            sumshares = sum(value for (_, _, value) in raw_receivers)

            if sumshares != 1:
                raise ValueError('Shares do not sum up to 1 (or 100%)')

            for (name, share) in raw_receivers:
                balances.append((name, Money(-amount * share, currency)))

        else:
            raise RuntimeError('Invalid modifier. This should not have happened')

        return (balances, amount)
