#!/usr/bin/env python3
# -*- coding: utf8 -*-

import argparse
import os
import re
import sys
from dateutil.parser import parse as parse_date
from datetime import datetime
from settle import IDENTIFIER_RE, IDENTIFIER_SPLIT_RE, FILE_CHARSET
from settle.balance import get_balances, settle_balances
from settle.group import Group
from settle.payment import Payment
from settle.reader import read_all_payments, store_payment
from settle.util import ask, debug, format_decimal

_identifier_re = re.compile(r'^%s$' % IDENTIFIER_RE)
_identifiers_re = re.compile(r'^(%%?%s%s)*%%?%s$' % (IDENTIFIER_RE, IDENTIFIER_SPLIT_RE, IDENTIFIER_RE))

class Commands:
    _funcdict = None

    def do_new(self, group, raw_args):
        p = argparse.ArgumentParser('create new payment')
        p.add_argument('amount', nargs='?')
        p.add_argument('receivers', nargs='*')
        args = p.parse_args(raw_args)

        if args.amount is None:
            amount = ask('Amount? ', require=r'^[0-9]*(\.[0-9]*)?$')
        else:
            amount = args.amount
            print('Amount: %s' % amount)

        if not args.receivers:
            receivers = ask('Receivers? ', 'Enter the names of the person(s) '
                            'the payment was done for. Separate multiple '
                            'persons by spaces. Use %name for a payment to a '
                            'list of people. ', require=_identifiers_re)
            #TODO: verify if the names are valid receivers
        else:
            receivers = args.receivers
            print('Receivers:', ' '.join(receivers))

        giver = ask('Who payed? ', default=group.default_giver)

        def _verify_date(d):
            try:
                parse_date(d)
            except ValueError:
                return 'Invalid date.'

        date = ask('Date? (- for none) ', default='now', forbidden=_verify_date)
        if date == 'now':
            date = datetime.now()
        elif date == '-':
            date = None
        else:
            date = parse_date(date)

        comment = ask('Comment? ', blank=True)

        p = Payment(group, giver, receivers, amount, date=date, comment=comment)
        debug('%r\n  %r' % (p, p.receivers.to_string()))
        store_payment(p)

    def do_print_balances(self, group, args):
        if len(args) > 1:
            raise ValueError('Too many arguments')

        balances = get_balances(group)

        filter_name = None
        if len(args) == 1:
            filter_name = args[0]
        elif len(args) > 1:
            raise ValueError('Too many arguments')

        for currency in balances:
            for name, val in balances[currency].items():
                if filter_name is None or name == filter_name:
                    print('%-12s %s %s' % (name, format_decimal(val), currency))

    def do_print_payments(self, group, args):
        if args:
            raise ValueError('Too many arguments')
        for payment in read_all_payments(group):
            print('%-14s %s%s' % (payment.giver, payment.datestr or '',
                  ('\n%s' % payment.comment if payment.comment else '')))
            for user, money in payment.balances:
                print('  %-12s %s' % (user, money))
            print()

    def do_settle_balances(self, group, args):
        for giver, receiver, money in settle_balances(group):
            print('%-12s -> %-12s %s %s' % (giver, receiver,
                format_decimal(money.value, sign=False), money.currency))

    def do_init(self, args):
        forbidden_groupnames = list(self.funcdict) + ['config', 'groups']

        group = None
        if len(args) == 1:
            if not _identifier_re.match(args[0]):
                print('Group identifier contains invalid characters.',
                      file=sys.stderr)
            elif args[0] in forbidden_groupnames:
                print('The given group identifier is a reserved name. Please '
                      'choose another.', file=sys.stderr)
            elif Group.try_load(args[0]):
                print('Group already exists: %s' % args[0], file=sys.stderr)
            else:
                group = args[0]
                print('Creating group with identifier `%s`\n' % group, file=sys.stderr)
        elif len(args) > 1:
            raise ValueError('Too many arguments')


        def _check_group(g):
            if g in forbidden_groupnames:
                return 'This is a reserved name. Please choose another.'
            if Group.try_load(g):
                return 'Group already exists: %s' % g

        while group is None:
            group = ask('Group identifier? ',
                        'Please choose a group identifier. It must only '
                        'contain letters, numbers, underscore and minus (and '
                        'start with a letter). Keep it short, as you will have '
                        'to type it often.\nGroup identifier? ',
                        require=_identifier_re, forbidden=_check_group)

        default_currency = ask('Default currency for this group? It is '
                               'recommended to use an abbreviation like EUR '
                               'and USD, but in fact can be everything. ',
                               forbidden=r'[\0-\x1f]')
        print('default currency: %r' % default_currency)
        print()

        default_giver = ask('Who are you? (not your name as written, but an '
                            'identifier like `simon` or `anna_meier`) ',
                            'Please enter who you are. This is used as the '
                            'default `giver` of a payment. Like the group '
                            'identifier, it must only contain only letters, '
                            'numbers, underscore and minus (and start with a '
                            'letter). You can leave this empty for now, but '
                            'then you will be asked for it every time.\n'
                            'Who are you? ',
                            require=_identifier_re, blank=True)

        os.mkdir(Group._path(group))
        os.mkdir(Group._path(group, 'payments'))

        with open(Group._path(group, 'config'), 'w', encoding=FILE_CHARSET) as f:
            f.write('default_currency: %s\n' % default_currency)

        with open(Group._path(group, 'localconfig'), 'w', encoding=FILE_CHARSET) as f:
            f.write('default_giver: %s\n' % default_giver)

        with open(Group._path(group, '.gitignore'), 'w', encoding=FILE_CHARSET) as f:
            f.write('localconfig\n')

    def run(self, args):
        args = args[:]
        if len(args) == 0:
            print('Error: No command given\nAvailable commands:', file=sys.stderr)
            for c in self.funcdict:
                print('  %s' % c, file=sys.stderr)
            return

        if args[0] == 'init':
            # special case because we don't pass a group here
            self.do_init(args[1:])
            return

        if args[0] in self.funcdict:
            args.insert(0, 'DEFAULTREPO') #TODO

        if len(args) <= 1:
            print('Error: No command given\nAvailable commands:', file=sys.stderr)
            for c in self.funcdict:
                print('  %s' % c, file=sys.stderr)
            return

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
