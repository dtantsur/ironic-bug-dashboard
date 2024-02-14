import os
import asyncio
import logging
import re
import json
import time

import aiohttp

CONFIG_DIR = 'configs'

LOG = logging.getLogger(__name__)

OPEN_STATUSES = {'New', 'In Progress', 'Triaged', 'Confirmed', 'Incomplete'}

PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

DEFAULT_SIZE = 100

DATE_RE = re.compile(r"(.*)T(.*)\..*\+(.*)")


def load_config(project_name):
    if project_name is None:
        return project_name

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, CONFIG_DIR)
    config_file = os.path.join(config_dir, f"{project_name}.json")

    LOG.info("config file: %s", config_file)
    LOG.info("=" * 80)

    config_data = {}
    try:
        with open(config_file, mode="r", encoding='utf-8') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        LOG.error("%s.json not found at %s", project_name, config_dir)

    return config_data


def reformat_date(date):
    if not date:
        return date

    m = DATE_RE.match(date)
    if not m:
        LOG.warning("%s cannot be parsed as a date", date)
        return date

    result = f"{m.group(1)} {m.group(2)}"
    if m.group(3) != "00:00":
        result = f"{result} UTC+{m.group(3)}"
    return result


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


def dedup(bugs):
    seen = set()
    result = []
    for bug in bugs:
        if bug['bug_link'] in seen:
            continue

        result.append(bug)
        seen.add(bug['bug_link'])

    return result


class _Client:

    TIMEOUT = 5
    CONCURRENCY_LIMIT = 5
    _update_after = 0

    def __init__(self, session, projects):
        self._session = session
        self._lock = asyncio.Lock()
        self._conditions = []
        self._limit = asyncio.Semaphore(self.CONCURRENCY_LIMIT)
        for item in projects:
            if isinstance(item, str):
                self._conditions.append({'project_name': item})
            else:
                self._conditions.append(item)

    async def fetch(self):
        async with self._lock:
            if self._update_after < time.time():
                LOG.debug('Updating bugs from launchpad')
                self._cache = await self._do_fetch()
                self._update_after = time.time() + self.TIMEOUT
            return self._cache

    async def _do_fetch(self):
        async with asyncio.TaskGroup() as tg:
            tasks = [(c['project_name'],
                      tg.create_task(self.search_bugs(**c)))
                     for c in self._conditions]

        return {key: task.result() for key, task in tasks}

    async def search_bugs(self, project_name, **conditions):
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
            async with self._limit:
                LOG.debug('Fetching %s from %s', params, url)
                async with self._session.get(url, params=params) as resp:
                    raw_result = await resp.json()

            for bug in raw_result['entries']:
                if bug['assignee_link'] is not None:
                    bug['assignee'] = bug['assignee_link'].split('~')[1]
                else:
                    bug['assignee'] = None

                bug['date_created'] = reformat_date(bug['date_created'])

                result.append(bug)

            url = raw_result.get('next_collection_link')
            params = []  # the link will contain everything

        return result


async def client(projects):
    # This call must be done inside an sync function, hence not in __init__
    session = aiohttp.ClientSession(raise_for_status=True)
    return _Client(session, projects)
