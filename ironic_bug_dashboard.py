from __future__ import print_function

import itertools

import requests


class IterableWithLength(object):
    def __init__(self, iters):
        self._iters = list(iters)

    def __iter__(self):
        return itertools.chain.from_iterable(self._iters)

    def __len__(self):
        print([len(x) for x in self._iters])
        return sum(len(x) for x in self._iters)


class Resource(object):
    url = None
    result = None

    def __init__(self, url, params):
        self.url = url
        self.params = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    self.params.append((key, item))
            else:
                self.params.append((key, value))

    def fetch(self):
        if self.result is not None:
            return

        result = requests.get(self.url, params=self.params)
        result.raise_for_status()
        self.result = result.json()


class Collection(Resource):
    def __iter__(self):
        self.fetch()
        return iter(self.result['entries'])

    def __len__(self):
        self.fetch()
        return len(self.result['entries'])


class Backend(object):
    PROJECTS = ('ironic', 'python-ironicclient')
    OPEN_STATUSES = ['New', 'In Progress', 'Triaged', 'Confirmed']

    _PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

    def __init__(self):
        self.projects = [self._PROJECT_TEMPLATE % p for p in self.PROJECTS]

    def search_bugs(self, **conditions):
        conditions.setdefault('status', self.OPEN_STATUSES)
        conditions['ws.op'] = 'searchTasks'
        return IterableWithLength(Collection(p, conditions)
                                  for p in self.projects)


STATS_TEMPLATE = (
    "Open: {total}. {new} new, {progress} in progress, "
    "{critical} critical, {high} high and {incomplete} incomplete"
)


def main():
    be = Backend()
    new_bugs = be.search_bugs(status='New')
    print("*** STATS ***")
    stats = STATS_TEMPLATE.format(
        total=len(be.search_bugs()),
        new=len(new_bugs),
        progress=len(be.search_bugs(status='In Progress')),
        critical=len(be.search_bugs(importance='Critical')),
        high=len(be.search_bugs(importance='High')),
        incomplete=len(be.search_bugs(status='Incomplete')),
    )
    print(stats)
    print("*** NEW BUGS ***")
    for bug in new_bugs:
        msg = "{bug[web_link]}\t{bug[title]}\t{bug[date_created]}"
        print(msg.format(bug=bug))


if __name__ == '__main__':
    main()
