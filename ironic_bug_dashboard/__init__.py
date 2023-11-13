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


def search_in_results(results, status=None, importance=None):
    result = []
    if isinstance(status, str):
        status = (status,)

    for bug in results['all']:
        if status is not None and bug['status'] not in status:
            continue
        if importance is not None and bug['importance'] != importance:
            continue
        result.append(bug)

    return result


PRIORITY_REQUIRED_STATUSES = simple_lp.OPEN_STATUSES - {'Incomplete'}
STATUS_PRIORITIES = {
    'In Progress': -10,
    'Triaged': -5,
    'Confirmed': -5
}


@aiohttp_jinja2.template('template.html')
async def index(request):
    ironic_bugs = {}
    nova_bugs = {}

    bugs = await request.app['lp_cache'].fetch()

    ironic_bugs['all'] = []
    for project in simple_lp.IRONIC_PROJECTS:
        if project not in bugs:
            continue
        ironic_bugs['all'].extend(bugs[project])
    LOG.debug('%d ironic bugs', len(ironic_bugs['all']))

    nova_bugs['all'] = bugs.get('nova', [])
    LOG.debug('%d nova bugs', len(nova_bugs['all']))

    critical_bugs = []
    for d in (ironic_bugs, nova_bugs):
        for status in ('New', 'Incomplete', 'In Progress'):
            d[status] = list(search_in_results(d, status=status))
        for importance in ('High', 'Critical', 'Wishlist'):
            d[importance] = list(search_in_results(
                d, importance=importance))
            if importance == 'Critical':
                critical_bugs.extend(d[importance])

    ironic_bugs['all'] = [x for x in ironic_bugs['all']
                          if x['importance'] != 'Wishlist']

    undecided = search_in_results(ironic_bugs,
                                  importance='Undecided',
                                  status=PRIORITY_REQUIRED_STATUSES)
    undecided.sort(key=lambda b: (STATUS_PRIORITIES.get(b['status'], 0),
                                  b['date_created']))

    ironic_new_confirmed = search_in_results(ironic_bugs,
                                             status=['New', 'Confirmed'])
    nova_new_confirmed = search_in_results(nova_bugs,
                                           status=['New', 'Confirmed'])
    new_or_confirmed = ironic_new_confirmed + nova_new_confirmed
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
        new_or_confirmed=new_or_confirmed,
        undecided=undecided,
        users=users,
        unassigned_in_progress=unassigned_in_progress,
        critical_bugs=critical_bugs,
    )


app.router.add_get('/', index)
app['lp_cache'] = simple_lp.Cache()


def main():
    logging.basicConfig(level=logging.DEBUG)
    try:
        web.run_app(app, host='127.0.0.1', port=8000)
    except KeyboardInterrupt:
        pass
