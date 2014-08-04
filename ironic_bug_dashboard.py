from __future__ import print_function

import itertools
import sys

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
            if isinstance(value, (list, set)):
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
    OPEN_STATUSES = set(['New', 'In Progress', 'Triaged', 'Confirmed',
                         'Incomplete'])

    PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

    def __init__(self):
        self.projects = [self.PROJECT_TEMPLATE % p for p in self.PROJECTS]

    def search_bugs(self, **conditions):
        conditions.setdefault('status', self.OPEN_STATUSES)
        conditions['ws.op'] = 'searchTasks'
        return IterableWithLength(Collection(p, conditions)
                                  for p in self.projects)


STATS_TEMPLATE = (
    "<h1>Stats</h1>"
    "<p>Open: {total}. {new} new, {progress} in progress, "
    "{critical} critical, {high} high and {incomplete} incomplete</p>"
    "<h2>New Bugs</h2>"
    "<p>Bugs that have 'New' status.</p>"
    "<ul>{new_bugs_html}</ul>"
    "<h2>Undecided Importance</h2>"
    "<p>Bugs that have 'Undecided' importance, but have status "
    "other than 'New' or 'Incomplete'.</p>"
    "<ul>{undecided_bugs_html}</ul>"
    "<h2>In Progress Bugs</h2>"
    "{assigned_bugs_html}"
    "<br><br>"  # Being a cool frontend developer
    "<a href=\"https://github.com/Divius/ironic-bug-dashboard\">"
    "Source code, pull requests, suggestions"
    "</a>"
)


BUG_TEMPLATE = (
    "<li>"
    "<a href=\"{bug[web_link]}\">{bug[title]}</a><br>"
    "created on {bug[date_created]}"
)


ASSIGNEE_TEMPLATE = (
    " assigned to "
    "<a href=\"https://launchpad.net/~{assignee}\">~{assignee}</a>"
)


app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
be = Backend()


def format_bug(bug, with_assignee=True):
    result = BUG_TEMPLATE.format(bug=bug)
    if with_assignee and bug['assignee_link'] is not None:
        assignee = bug['assignee_link'].split('~')[1]
        result += ASSIGNEE_TEMPLATE.format(bug=bug,
                                           assignee=assignee)
    return result


def format_bugs(bugs, with_assignee=True):
    return ''.join(format_bug(bug, with_assignee=with_assignee)
                   for bug in bugs)


@app.route("/")
@cache.cached(timeout=300)
def index():
    new_bugs = be.search_bugs(status='New')
    undecided_bugs = be.search_bugs(importance='Undecided',
                                    status=be.OPEN_STATUSES -
                                    set(['New', 'Incomplete']))
    in_progress_bugs = be.search_bugs(status='In Progress')

    users = {}
    for bug in in_progress_bugs:
        assignee = (bug['assignee_link'].split('~')[1]
                    if bug['assignee_link'] is not None
                    else '!!! Unassigned !!!')
        users.setdefault(assignee, []).append(bug)
    assigned_bugs_html = ''.join(
        '<h3>{assignee}</h3><ul>{bugs}</ul>'.format(
            assignee=assignee,
            bugs=format_bugs(bugs, False)
        )
        for (assignee, bugs) in sorted(users.items(), key=lambda x: x[1]))

    stats = STATS_TEMPLATE.format(
        total=len(be.search_bugs()),
        new=len(new_bugs),
        progress=len(in_progress_bugs),
        critical=len(be.search_bugs(importance='Critical')),
        high=len(be.search_bugs(importance='High')),
        incomplete=len(be.search_bugs(status='Incomplete')),
        new_bugs_html=format_bugs(new_bugs),
        undecided_bugs_html=format_bugs(undecided_bugs),
        assigned_bugs_html=assigned_bugs_html,
    )
    return stats


if __name__ == '__main__':
    try:
        debug = sys.argv[1] == '--debug'
    except IndexError:
        debug = False
    app.run(debug=debug)
