#!/usr/bin/env python3
# -*- coding: utf8 -*-

import argparse
import sys
import settle
from settle.balance import get_balances
from settle.group import Group
from settle.reader import read_all_payments
from settle.util import debug, format_decimal

class Commands:
    _funcdict = None

    def do_new(self, group, raw_args):
        p = argparse.ArgumentParser('create new payment')
        p.add_argument('amount', nargs='?')
        p.add_argument('receivers', nargs='*')
        args = p.parse_args(raw_args)
        print('new group={} args={}'.format(group, args))

    def do_print_balances(self, group, args):
        if len(args) > 1:
            raise ValueError('Too many arguments')

        balances = get_balances(group)

        def _p(name):
            print('%s:' % name)
            for c, v in balances[name].items():
                print('    %s %s' % (c, format_decimal(v)))

        if len(args) == 1:
            name = args[0]
            bal = get_balances(group)
            if name in bal:
                _p(name)
            else:
                raise ValueError('Person not found: %s' % name)
        else:
            for name in balances:
                _p(name)

    def do_print_payments(self, group, args):
        if args:
            raise ValueError('Too many arguments')
        for payment in read_all_payments(group):
            print('%-10s %s %s' % (payment.giver, payment.comment or '', payment.time or ''))
            for user, money in payment.balances:
                print('  %-10s %s' % (user, money))
            print()


    def run(self, args):
        args = args[:]
        if len(args) == 0:
            print('Error: No command given\nAvailable commands:', file=sys.stderr)
            for c in self.funcdict:
                print('  %s' % c, file=sys.stderr)
            return

        if args[0] in self.funcdict:
            args.insert(0, 'DEFAULTREPO') #TODO

        group = Group.load(args[0])
        cmd = args[1]
        rest = args[2:]

        try:
            f = self.funcdict[cmd]
        except KeyError:
            print('no such command: %s' % cmd, file=sys.stderr)
        else:
            debug('running %s(%s) with %r' % (cmd, rest, group))
            f(group, rest)

    @property
    def funcdict(self):
        if self._funcdict is None:
            self._funcdict = {}
            for f in dir(self):
                if f.startswith('do_'):
                    k = f[3:].replace('_', '-')
                    self._funcdict[k] = getattr(self, f)

        return self._funcdict


if __name__ == '__main__':
    Commands().run(sys.argv[1:])
