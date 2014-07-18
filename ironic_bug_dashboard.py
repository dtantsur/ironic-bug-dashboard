from __future__ import print_function

import itertools
import json

from launchpadlib import launchpad
import xdg.BaseDirectory


class IterableWithLength(object):
    def __init__(self, projects, conditions):
        self._iters = [p.searchTasks(**conditions) for p in projects]

    def __iter__(self):
        return itertools.chain.from_iterable(self._iters)

    def __len__(self):
        return sum(len(x) for x in self._iters)


class Backend(object):
    CACHE_DIR = xdg.BaseDirectory.save_cache_path('ironic-bug-dashboard')
    PROJECTS = ('ironic', 'python-ironicclient')
    OPEN_STATUSES = ['New', 'In Progress', 'Triaged', 'Confirmed']

    def __init__(self):
        self.lp = launchpad.Launchpad.login_anonymously('Ironic Bug Dashboard',
                                                        'production',
                                                        self.CACHE_DIR)
        self.projects = [self.lp.projects[name] for name in self.PROJECTS]

    def search_bugs(self, **conditions):
        conditions.setdefault('status', self.OPEN_STATUSES)
        return IterableWithLength(self.projects, conditions)


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
        msg = "{bug.web_link}\t{bug.title}\t{bug.date_created}"
        print(msg.format(bug=bug))


if __name__ == '__main__':
    main()
