# -*- coding: utf-8 -*-
from collections import defaultdict
from decimal import Decimal
from settle.reader import read_all_payments

def get_balances(group):
    users = defaultdict(lambda: defaultdict(Decimal))
    for payment in read_all_payments(group):
        for user, money in payment.balances:
            users[user][money.currency] += money.value

    return users
