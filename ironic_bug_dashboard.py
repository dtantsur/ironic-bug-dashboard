from __future__ import print_function

import itertools

from flask import Flask
from flask.ext.cache import Cache
import requests


class IterableWithLength(object):
    def __init__(self, iters):
        self._iters = list(iters)

    def __iter__(self):
        return itertools.chain.from_iterable(self._iters)

    def __len__(self):
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
    "<h1>Stats</h1>"
    "<p>Open: {total}. {new} new, {progress} in progress, "
    "{critical} critical, {high} high and {incomplete} incomplete</p>"
    "<h2>New bugs</h2>"
    "<ul>{new_bugs_html}</ul>"
)


BUG_TEMPLATE = (
    "<li>"
    "<a href=\"{bug[web_link]}\">{bug[title]}</a> "
    "({bug[date_created]})"
)


def main():
    app = Flask(__name__)
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    be = Backend()

    @app.route("/")
    @cache.cached(timeout=50)
    def index():
        new_bugs = be.search_bugs(status='New')
        stats = STATS_TEMPLATE.format(
            total=len(be.search_bugs()),
            new=len(new_bugs),
            progress=len(be.search_bugs(status='In Progress')),
            critical=len(be.search_bugs(importance='Critical')),
            high=len(be.search_bugs(importance='High')),
            incomplete=len(be.search_bugs(status='Incomplete')),
            new_bugs_html=''.join(BUG_TEMPLATE.format(bug=bug)
                                  for bug in new_bugs)
        )
        return stats

    app.run()


if __name__ == '__main__':
    main()
