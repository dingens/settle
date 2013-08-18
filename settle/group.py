# -*- coding: utf-8 -*-
import os
import settle
from settle.reader import read_file
from settle.payment import Receivers
from settle.util import debug

class Group:
    def __init__(self, name, default_currency, lists=None):
        self.name = name
        self.default_currency = default_currency
        self.lists = lists or {}

    def __repr__(self):
        return 'Group(%r, default_currency=%r)' % (self.name, self.default_currency)

    @classmethod
    def load(cls, name):
        from settle import DEFAULT_CURRENCY

        config = read_file(cls._path(name, 'config'), {})
        default_currency = config.get('default_currency', DEFAULT_CURRENCY)
        g = cls(name, default_currency=default_currency)

        lists_ = read_file(cls._path(name, 'lists'), {})
        for name, s in lists_.items():
            debug('parse receivers: %s' % s)
            g.lists[name] = Receivers.from_string(g, s, is_list=True)

        return g

    def path(self, subdir=None):
        return self.__class__._path(self.name, subdir)

    @classmethod
    def _path(cls, name, subdir):
        p = os.path.join(os.path.expanduser('~'), '.settle', name)
        if subdir is None:
            return p
        return os.path.join(p, subdir)
