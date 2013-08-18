# -*- coding: utf-8 -*-
import os
from settle.reader import read_file
from settle.payment import Receivers
from settle.util import debug

class Group:
    def __init__(self, name, default_currency, default_giver, lists=None):
        self.name = name
        self.default_currency = default_currency
        self.default_giver = default_giver
        self.lists = lists or {}

    def __repr__(self):
        return 'Group(%r)' % self.name

    @classmethod
    def load(cls, name):
        from settle import DEFAULT_CURRENCY
        args = {}

        if not os.path.isdir(Group._path(name)):
            raise NoSuchGroupError(name)

        config = read_file(cls._path(name, 'config'), {})
        config.update(read_file(cls._path(name, 'localconfig'), {}))
        args['default_currency'] = config.get('default_currency', DEFAULT_CURRENCY)
        args['default_giver'] = config.get('default_giver', None)
        g = cls(name, **args)

        lists_ = read_file(cls._path(name, 'lists'), {})
        for name, s in lists_.items():
            debug('parse receivers: %s' % s)
            g.lists[name] = Receivers.from_string(g, s, is_list=True)

        return g

    @classmethod
    def try_load(cls, name):
        try:
            return cls.load(name)
        except NoSuchGroupError:
            return None

    def path(self, *subdirs):
        return self.__class__._path(self.name, *subdirs)

    @classmethod
    def _path(cls, name, *subdirs):
        p = os.path.join(os.path.expanduser('~'), '.settle', name)
        return os.path.join(p, *subdirs)

class NoSuchGroupError(Exception):
    pass
