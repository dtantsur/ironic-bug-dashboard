import itertools

import requests


PROJECT_NAMES = ('ironic', 'python-ironicclient')
OPEN_STATUSES = set(['New', 'In Progress', 'Triaged', 'Confirmed',
                     'Incomplete'])

PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

_PROJECTS = [PROJECT_TEMPLATE % p for p in PROJECT_NAMES]


def get_json(url, params):
    result = requests.get(url, params=params)
    result.raise_for_status()
    return result.json()


class IterableWithLength(object):
    def __init__(self, iters):
        self._iters = list(iters)

    def __iter__(self):
        return itertools.chain.from_iterable(self._iters)

    def __len__(self):
        return sum(len(x) for x in self._iters)


class Collection(object):
    url = None
    result = None

    def __init__(self, url, params=None):
        self.url = url
        self.params = []
        if params:
            for key, value in params.items():
                if isinstance(value, (list, set)):
                    for item in value:
                        self.params.append((key, item))
                else:
                    self.params.append((key, value))

    def fetch(self):
        if self.result is not None:
            return
        self.result = get_json(self.url, self.params)

    def __iter__(self):
        self.fetch()
        if 'next_collection_link' in self.result:
            return itertools.chain(
                self.result['entries'],
                Collection(self.result['next_collection_link']))
        else:
            return iter(self.result['entries'])

    def __len__(self):
        self.fetch()
        return self.result['total_size']


def search_bugs(**conditions):
    conditions.setdefault('status', OPEN_STATUSES)
    conditions['ws.op'] = 'searchTasks'
    return IterableWithLength(Collection(p, conditions)
                              for p in _PROJECTS)
