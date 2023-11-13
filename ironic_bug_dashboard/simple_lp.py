import aiohttp


IRONIC_PROJECTS = ('ironic', 'python-ironicclient', 'ironic-lib',
                   'ironic-python-agent', 'sushy', 'networking-baremetal',
                   'virtualbmc', 'virtualpdu')
INSPECTOR_PROJECTS = ('ironic-inspector', 'python-ironic-inspector-client')

OPEN_STATUSES = set(['New', 'In Progress', 'Triaged', 'Confirmed',
                     'Incomplete'])

PROJECT_TEMPLATE = 'https://api.launchpad.net/1.0/%s'

DEFAULT_SIZE = 100


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
    keys = IRONIC_PROJECTS + INSPECTOR_PROJECTS + ('nova',)
    conditions = [{'project_name': project}
                  for project in IRONIC_PROJECTS + INSPECTOR_PROJECTS]
    conditions.append({'project_name': 'nova', 'tags': 'ironic'})

    async with aiohttp.ClientSession(raise_for_status=True) as session:
        values = [await search_bugs(session, **c) for c in conditions]

    return dict(zip(keys, values))
