import logging
import os

from aiohttp import web
import aiohttp_jinja2
import jinja2

from . import simple_lp


LOG = logging.getLogger(__name__)

app = web.Application()
template_path = os.path.dirname(os.path.realpath(__file__))
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path))


def search_in_cache(cache, status=None, importance=None):
    if isinstance(status, str):
        status = (status,)

    for bug in cache['all']:
        if status is not None and bug['status'] not in status:
            continue
        if importance is not None and bug['importance'] != importance:
            continue
        yield bug


PRIORITY_REQUIRED_STATUSES = simple_lp.OPEN_STATUSES - {'Incomplete'}
STATUS_PRIORITIES = {
    'In Progress': -10,
    'Triaged': -5,
    'Confirmed': -5
}


@aiohttp_jinja2.template('template.html')
async def index(_request):
    LOG.debug('updating bugs')
    ironic_bugs = {}
    nova_bugs = {}
    inspector_bugs = {}

    bugs = await simple_lp.fetch_all()

    ironic_bugs['all'] = []
    for project in simple_lp.IRONIC_PROJECTS:
        if project not in bugs:
            continue
        ironic_bugs['all'].extend(bugs[project])
    LOG.debug('%d ironic bugs', len(ironic_bugs['all']))

    if 'nova' in bugs:
        nova_bugs['all'] = bugs['nova']
    else:
        nova_bugs['all'] = []
    LOG.debug('%d nova bugs', len(nova_bugs['all']))

    inspector_bugs['all'] = []
    for project in simple_lp.INSPECTOR_PROJECTS:
        if project not in bugs:
            continue
        inspector_bugs['all'].extend(bugs[project])
    LOG.debug('%d inspector bugs', len(inspector_bugs['all']))

    critical_bugs = []
    for d in (ironic_bugs, nova_bugs, inspector_bugs):
        for status in ('New', 'Incomplete', 'In Progress'):
            d[status] = list(search_in_cache(d, status=status))
        for importance in ('High', 'Critical', 'Wishlist'):
            d[importance] = list(search_in_cache(
                d, importance=importance))
            if importance == 'Critical':
                critical_bugs.extend(d[importance])

    for d in (ironic_bugs, inspector_bugs):
        d['all'] = [x for x in d['all'] if x['importance'] != 'Wishlist']

    ironic_undecided = search_in_cache(ironic_bugs,
                                       importance='Undecided',
                                       status=PRIORITY_REQUIRED_STATUSES)

    inspector_undecided = search_in_cache(inspector_bugs,
                                          importance='Undecided',
                                          status=PRIORITY_REQUIRED_STATUSES)
    undecided = list(ironic_undecided) + list(inspector_undecided)
    undecided.sort(key=lambda b: (STATUS_PRIORITIES.get(b['status'], 0),
                                  b['date_created']))

    ironic_new_confirmed = search_in_cache(ironic_bugs,
                                           status=['New', 'Confirmed'])
    nova_new_confirmed = search_in_cache(nova_bugs,
                                         status=['New', 'Confirmed'])
    new_or_confirmed = list(ironic_new_confirmed) + list(nova_new_confirmed)
    new_or_confirmed.sort(key=lambda b: (b['status'] != 'New',
                                         b['date_created']))

    users = {}
    unassigned_in_progress = []
    for bug in ironic_bugs['In Progress']:
        assignee = bug['assignee']
        if assignee:
            users.setdefault(assignee, []).append(bug)
        else:
            unassigned_in_progress.append(bug)

    return dict(
        ironic_bugs=ironic_bugs,
        nova_bugs=nova_bugs,
        inspector_bugs=inspector_bugs,
        new_or_confirmed=new_or_confirmed,
        undecided=undecided,
        users=users,
        unassigned_in_progress=unassigned_in_progress,
        critical_bugs=critical_bugs,
    )


app.router.add_get('/', index)


def main():
    logging.basicConfig(level=logging.DEBUG)
    try:
        web.run_app(app, host='127.0.0.1', port=8000)
    except KeyboardInterrupt:
        pass
