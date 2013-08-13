# -*- coding: utf-8 -*-
import os

class Group:
    def __init__(self, name, default_currency):
        self.name = name
        self.default_currency = default_currency

    def __repr__(self):
        return 'Group(%r, default_currency=%r)' % (self.name, self.default_currency)

    @classmethod
    def load(cls, name):
        return cls(name, default_currency='EUR') # todo

    def dir(self, subdir=None):
        p = os.path.join(os.path.expanduser('~'), '.settle', self.name)
        if subdir is None:
            return p
        return os.path.join(p, subdir)

