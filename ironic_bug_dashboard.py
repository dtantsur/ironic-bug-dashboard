from __future__ import print_function

import itertools
import json

from launchpadlib import launchpad
import xdg.BaseDirectory


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
        return itertools.chain(*(p.searchTasks(**conditions)
                                 for p in self.projects))

    def new_bugs(self):
        return self.search_bugs(status='New')


def main():
    be = Backend()
    print("*** NEW BUGS ***")
    for bug in be.new_bugs():
        print(bug, '\t', bug.title)


if __name__ == '__main__':
    main()
