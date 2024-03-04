import datetime
import logging
import os
import sys

from aiohttp import web
import aiohttp_jinja2
import jinja2

from . import simple_lp


LOG = logging.getLogger(__name__)

app = web.Application()
template_path = os.path.dirname(os.path.realpath(__file__))
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_path))

project_name = os.getenv('PROJECT_NAME')

config = simple_lp.load_config(project_name)
if not config:
    LOG.error('Configuration file cannot be empty.')
    sys.exit(1)

PROJECTS = config.get('projects', [])
TAGGED_PROJECTS = config.get('tagged_projects', [])
ALL_PROJECTS = PROJECTS + TAGGED_PROJECTS
PRIORITY_REQUIRED_STATUSES = config.get('priority_required_statuses', [])
STATUS_PRIORITIES = config.get('status_priorities', [])


@aiohttp_jinja2.template('template.html')
async def index(request):
    ironic_bugs = {}
    nova_bugs = {}

    if 'lp' not in request.app:
        LOG.info('Creating a new launchpad client')
        request.app['lp'] = await simple_lp.client(ALL_PROJECTS)

    bugs = await request.app['lp'].fetch()

    ironic_bugs['all'] = []
    for project in PROJECTS:
        if project not in bugs:
            continue
        ironic_bugs['all'].extend(bugs[project])
    LOG.debug('%d ironic bugs', len(ironic_bugs['all']))

    nova_bugs['all'] = bugs.get('nova', [])
    LOG.debug('%d nova bugs', len(nova_bugs['all']))

    critical_bugs = []
    for d in (ironic_bugs, nova_bugs):
        for status in ('New', 'Incomplete', 'In Progress'):
            d[status] = list(simple_lp.search_in_results(d, status=status))
        for importance in ('High', 'Critical', 'Wishlist'):
            d[importance] = list(simple_lp.search_in_results(
                d, importance=importance))
            if importance == 'Critical':
                critical_bugs.extend(d[importance])

    ironic_bugs['all'] = [x for x in ironic_bugs['all']
                          if x['importance'] != 'Wishlist']

    nova_triaged_bugs = []
    nova_triage_needed_bugs = []
    for bug in nova_bugs['all']:
        if (bug['status'] == 'New' or bug['importance'] == 'Undecided'):
            nova_triage_needed_bugs.append(bug)
        else:
            nova_triaged_bugs.append(bug)
    nova_triaged_bugs.sort(
        key=lambda b: (STATUS_PRIORITIES.get(b['status'], 0),
                       b['date_created']))

    nova_bugs['all'] = nova_triage_needed_bugs

    undecided = simple_lp.search_in_results(
        ironic_bugs,
        importance='Undecided',
        status=PRIORITY_REQUIRED_STATUSES)
    undecided.sort(key=lambda b: (STATUS_PRIORITIES.get(b['status'], 0),
                                  b['date_created']))

    ironic_new_confirmed = simple_lp.search_in_results(
        ironic_bugs, status=['New', 'Confirmed'])
    nova_new_confirmed = simple_lp.search_in_results(
        nova_bugs, status=['New', 'Confirmed'])
    triage_needed = simple_lp.dedup(
        ironic_new_confirmed + nova_new_confirmed + undecided)
    triage_needed.sort(key=lambda b: (b['status'] != 'New', b['date_created']))

    users = {}
    unassigned_in_progress = []
    for bug in ironic_bugs['In Progress']:
        assignee = bug['assignee']
        if assignee:
            users.setdefault(assignee, []).append(bug)
        else:
            unassigned_in_progress.append(bug)

    threshold = (datetime.datetime.now(datetime.timezone.utc)
                 - datetime.timedelta(days=365))
    threshold = threshold.isoformat(sep=' ', timespec='seconds')
    LOG.debug('Considering bugs ancient before %s', threshold)
    ancient_bugs = [bug for bug in ironic_bugs['all']
                    if bug['date_created'] < threshold]
    ancient_bugs.sort(key=lambda b: b['date_created'])

    return dict(
        ironic_bugs=ironic_bugs,
        nova_bugs=nova_bugs,
        nova_triaged_bugs=nova_triaged_bugs,
        triage_needed=triage_needed,
        users=users,
        unassigned_in_progress=unassigned_in_progress,
        critical_bugs=critical_bugs,
        ancient_bugs=ancient_bugs,
    )


app.router.add_get('/', index)


def main():
    logging.basicConfig(level=logging.DEBUG)

    LOG.info("Configuration options gathered from: environment variables: %s",
             project_name)

    try:
        web.run_app(app, host='127.0.0.1', port=8000)
    except KeyboardInterrupt:
        pass
