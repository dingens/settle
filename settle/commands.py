#!/usr/bin/env python3
# -*- coding: utf8 -*-

import argparse
import sys
from settle.balance import get_balances
from settle.group import Group
from settle.util import debug

class Commands:
    _funcdict = None

    def do_new(self, group, raw_args):
        p = argparse.ArgumentParser('create new payment')
        p.add_argument('amount', nargs='?')
        p.add_argument('receivers', nargs='*')
        args = p.parse_args(raw_args)
        print('new group={} args={}'.format(group, args))

    def do_print_balances(self, group, args):
        print('print balances for %s %s' % (group, args))
        for name, currencies in get_balances(group).items():
            print('%s:' % name)
            for c, v in currencies.items():
                print('    %s %s' % (c, v))

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
