# -*- coding: utf-8 -*-
from collections import defaultdict, deque, namedtuple
from decimal import Decimal
from functools import partial
from operator import itemgetter
from settle.reader import read_all_payments
from settle.util import Money

Balance = namedtuple('Balance', ('name', 'value'))
Transfer = namedtuple('Transfer', ('giver', 'receiver', 'value'))

def get_balances(group):
    currencies = defaultdict(lambda: defaultdict(Decimal))
    for payment in read_all_payments(group):
        for user, money in payment.balances:
            currencies[money.currency][user] += money.value

    return currencies

def settle_balances(group):
    all_balances = get_balances(group)
    balancesorted = partial(sorted, key=itemgetter(1))
    for currency, raw_balances in all_balances.items():
        balances = balancesorted(raw_balances.items())
        balances = [Balance(n,v) for (n,v) in balances]

        for _ in range(len(balances)): # ensure termination
            poorest = balances.pop(0)
            richest = balances.pop() #last
            transfer = min(abs(richest.value), abs(poorest.value))
            yield Transfer(poorest.name, richest.name, Money(transfer, currency))

            richest = Balance(richest.name, richest.value - transfer)
            poorest = Balance(poorest.name, poorest.value + transfer)
            # there may be rounding problems (e.g. 1/3) where we won't get zero
            if round(richest.value, 10) != 0:
                balances.append(richest)
            if round(poorest.value, 10) != 0:
                balances.append(poorest)

            balances = balancesorted(balances)

            if not balances:
                break

        if balances:
            raise RuntimeError('balances left. this should not happen')
