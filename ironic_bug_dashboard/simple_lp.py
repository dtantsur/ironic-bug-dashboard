import itertools
import multiprocessing

import requests


IRONIC_PROJECTS = ('ironic', 'python-ironicclient', 'ironic-lib',
                   'ironic-python-agent', 'sushy')
INSPECTOR_PROJECTS = ('ironic-inspector', 'python-ironic-inspector-client')

OPEN_STATUSES = set(['New', 'In Progress', 'Triaged', 'Confirmed',
                     'Incomplete'])

PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'


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


def search_bugs(project_name, **conditions):
    conditions.setdefault('status', OPEN_STATUSES)
    conditions['ws.op'] = 'searchTasks'
    conditions['ws.size'] = '300'
    for bug in Collection(PROJECT_TEMPLATE % project_name, conditions):
        if bug['assignee_link'] is not None:
            bug['assignee'] = bug['assignee_link'].split('~')[1]
        else:
            bug['assignee'] = None
        yield bug


def _fetch_bugs(conditions):
    return list(search_bugs(**conditions))


def fetch_all():
    keys = IRONIC_PROJECTS + INSPECTOR_PROJECTS + ('nova',)
    conditions = [{'project_name': project}
                  for project in IRONIC_PROJECTS + INSPECTOR_PROJECTS]
    conditions.append({'project_name': 'nova', 'tags': 'ironic'})

    pool = multiprocessing.Pool()
    try:
        values = pool.map(_fetch_bugs, conditions)
    finally:
        pool.close()
    return dict(zip(keys, values))
