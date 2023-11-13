import asyncio
import logging
import time

import aiohttp


LOG = logging.getLogger(__name__)


IRONIC_PROJECTS = (
    'bifrost',
    'ironic',
    'ironic-inspector',
    'ironic-lib',
    'ironic-prometheus-exporter',
    'ironic-python-agent',
    'ironic-python-agent-builder',
    'ironic-ui',
    'metalsmith',
    'networking-baremetal',
    'python-ironic-inspector-client',
    'python-ironicclient',
    'sushy',
    'sushy-tools',
    'virtualbmc',
    'virtualpdu',
)

OPEN_STATUSES = set(['New', 'In Progress', 'Triaged', 'Confirmed',
                     'Incomplete'])

PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

DEFAULT_SIZE = 100

CONCURRENCY_LIMIT = asyncio.Semaphore(5)


async def search_bugs(session, project_name, **conditions):
    conditions.setdefault('status', OPEN_STATUSES)
    conditions['ws.op'] = 'searchTasks'
    conditions['ws.size'] = str(DEFAULT_SIZE)

    url = PROJECT_TEMPLATE % project_name
    params = []
    for key, value in conditions.items():
        if isinstance(value, (list, set)):
            for item in value:
                params.append((key, item))
        else:
            params.append((key, value))

    result = []
    while url:
        async with CONCURRENCY_LIMIT:
            LOG.debug('Fetching %s from %s', params, url)
            async with session.get(url, params=params) as resp:
                raw_result = await resp.json()

        for bug in raw_result['entries']:
            if bug['assignee_link'] is not None:
                bug['assignee'] = bug['assignee_link'].split('~')[1]
            else:
                bug['assignee'] = None

            result.append(bug)

        url = raw_result.get('next_collection_link')
        params = []  # the link will contain everything

    return result


async def fetch_all():
    keys = IRONIC_PROJECTS + ('nova',)
    conditions = [{'project_name': project} for project in IRONIC_PROJECTS]
    conditions.append({'project_name': 'nova', 'tags': 'ironic'})

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(search_bugs(session, **c))
                     for c in conditions]

    return {key: task.result() for key, task in zip(keys, tasks)}


class Cache:

    TIMEOUT = 5
    _update_after = 0

    def __init__(self):
        self._lock = asyncio.Lock()

    async def fetch(self):
        async with self._lock:
            if self._update_after < time.time():
                LOG.debug('updating bugs from launchpad')
                self._cache = await fetch_all()
                self._update_after = time.time() + self.TIMEOUT
            return self._cache
