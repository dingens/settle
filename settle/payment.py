import re
from collections import defaultdict
from decimal import Decimal
from settle.util import shorten

_receiver_re = re.compile('^([A-Za-z][-_A-Za-z0-9]*)(?:([%=*])([0-9.]+))?$')

class Payment:
    def __init__(self, group, receivers, amount=None, giver=None, currency=None, time=None, comment=None):
        self.group = group
        self.receivers = tuple(receivers) # we don't want an iterator
        self.amount = amount if amount is None else Decimal(amount)
        self.giver = giver
        self.currency = currency or group.default_currency
        self.time = time
        self.comment = comment
        self._calculate_balances()

    def __repr__(self):
        return 'Payment(group=%r, receivers=%r, amount=%r, giver=%r, currency=%r, time=%r, comment=%r)' % (
            self.group, self.receivers, self.amount, self.giver, self.currency, self.time, shorten(self.comment, 50))

    def _calculate_balances(self):
        from settle.reader import ReaderValueError
        self.balances = defaultdict(Decimal)
        modifiers = {r.modifier for r in self.receivers}
        if len(modifiers) > 1:
            if None in modifiers and 'factor' in modifiers:
                modifiers.discard(None)
            else:
                raise ValueError('Different receiver modifiers in one payment')

        # equally balanced
        if len(modifiers) == 0:
            if self.amount is None:
                raise ReaderValueError('Required field amount missing')
            for r in receivers:
                self.balances[r.name] -= self.amount / len(self.receivers)
            self.balances[self.giver] += self.amount
            return

        mod, = modifiers

        if mod == 'factor':
            if self.amount is None:
                raise ReaderValueError('Required field amount missing')

            for r in self.receivers:
                if r.value is None:
                    r.value = 1

            sumfactors = sum(r.value for r in self.receivers)
            for r in self.receivers:
                self.balances[r.name] -= self.amount * r.value / sumfactors
            self.balances[self.giver] += self.amount

        elif mod == 'amount':
            sumamounts = 0
            for r in self.receivers:
                if r.value is None:
                    raise ValueError('Exact amount specified for some but not all receivers')

                self.balances[r.name] -= r.value
                sumamounts += r.value

            if self.amount is not None and self.amount != sumamounts:
                raise ValueError('Sum of amounts does not match the supplied payment amount')

            self.balances[self.giver] += sumamounts

        elif mod == 'share':
            if self.amount is None:
                raise ReaderValueError('Required field amount missing')
            sumshares = 0
            for r in self.receivers:
                if r.value is None:
                    raise ValueError('Share specified for some but not all receivers')
                sumshares += r.value

            if sumshares != 1:
                raise ValueError('Shares do not sum up to 1 (or 100%)')

            for r in self.receivers:
                self.balances[r.name] -= r.value * self.amount

        else:
            raise RuntimeError('Invalid modifier. This should not have happened')


class Receiver:
    def __init__(self, name, modifier=None, value=None):
        self.name = name
        self.modifier = modifier
        self.value = value

    def __repr__(self):
        return 'Receiver(%r, modifier=%r, value=%r)' % (self.name, self.modifier, self.value)

    @classmethod
    def from_string(cls, s):
        m = _receiver_re.match(s)
        if m is None:
            raise ValueError('Could not parse receiver information: %r' % s)
        name, modifier, value_ = m.groups()

        if modifier is None:
            return cls(name)

        value = Decimal(value_)
        if modifier == '%':
            return cls(name, 'share', value/100)
        if modifier == '*':
            return cls(name, 'factor', value)
        if modifier == '=':
            return cls(name, 'amount', value)


class Group:
    def __init__(self, default_currency):
        self.default_currency = default_currency
