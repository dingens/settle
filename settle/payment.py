import re
from collections import defaultdict
from decimal import Decimal
from settle import IDENTIFIER_RE, IDENTIFIER_SPLIT_RE
from settle.util import debug, is_list, Money, shorten, format_datetime

_receiver_re = re.compile(r'^(%?' + IDENTIFIER_RE + r')(?:([%=*])([0-9.]+))?$')
_receivers_split_re = re.compile(IDENTIFIER_SPLIT_RE)


class Payment:
    def __init__(self, group, giver, receivers, amount=None, currency=None, date=None, comment=None):
        self.group = group
        self.giver = giver
        if isinstance(receivers, str):
            self.receivers = Receivers.from_string(group, receivers)
        else:
            assert receivers.group == self.group
            self.receivers = receivers
        self.amount = amount if amount is None else Decimal(amount)
        self.given_currency = currency
        self.currency = currency or group.default_currency
        self.date = date
        self.comment = comment
        self._calculate_balances()

    def __repr__(self):
        return 'Payment(group=%r, giver=%r, receivers=%r, amount=%r, currency=%r, date=%r, comment=%r)' % (
            self.group, self.giver, self.receivers, self.amount, self.currency, self.date, shorten(self.comment, 50))

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

    @property
    def datestr(self):
        return format_datetime(self.date)

    def serialize(self):
        return dict(
            giver=self.giver,
            receivers=self.receivers.to_string(),
            amount=self.amount,
            currency=self.given_currency,
            date=self.datestr,
            comment=self.comment,
        )


class Receivers:
    def __init__(self, group, raw_receivers, modifier):
        self.group = group
        self.raw_receivers = tuple(raw_receivers)
        self.modifier = modifier

    def __repr__(self):
        return '<Receivers group=%s, %d receivers>' % (
            self.group.name, len(self.raw_receivers))

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
                value = Decimal(1)
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

    def to_string(self):
        res = []
        if self.modifier == '*':
            for name, factor in self.raw_receivers:
                if factor == 1:
                    res.append(name)
                else:
                    res.append('%s*%s' % (name, factor))
        elif self.modifier in '=%':
            for name, val in self.raw_receivers:
                res.append('%s%s%s' % (name, self.modifier, val))
        return ' '.join(res)
