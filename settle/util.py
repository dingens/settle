# -*- coding: utf-8 -*-

def shorten(s, length, allow_none=True):
    if s is None and allow_none:
        return ''
    if len(s) <= length:
        return s
    else:
        return s[:length-4] + ' ...'

def lowercase_keys(d):
    """Return a copy of dictionary `d` with keys lowercased"""
    return {k.lower(): v for k, v in d.items()}
