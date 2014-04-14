DEFAULT_CURRENCY = 'EUR'
MAX_LIST_RESOLVER_RECURSION_DEPTH = 16
IDENTIFIER_RE = r'[A-Za-z][-_A-Za-z0-9]*'
IDENTIFIER_SPLIT_RE = ',?[ \t\r\n]+'
FILE_CHARSET = 'utf-8'

from settle import balance, commands, group, payment, reader, util
