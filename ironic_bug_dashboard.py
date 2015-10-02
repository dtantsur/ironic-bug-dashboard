import logging
import sys

from flask import Flask
import jinja2

from simple_lp import search_bugs, search_nova_bugs, OPEN_STATUSES


LOG = logging.getLogger(__name__)


app = Flask(__name__)


def search_in_cache(cache, status=None, importance=None):
    if isinstance(status, str):
        status = (status,)

    for bug in cache['all']:
        if status is not None and bug['status'] not in status:
            continue
        if importance is not None and bug['importance'] != importance:
            continue
        yield bug


TRIAGED_STATUSES = OPEN_STATUSES - {'New', 'Incomplete'}


@app.route("/")
def index():
    LOG.debug('updating bugs')
    ironic_bugs = {}
    nova_bugs = {}

    ironic_bugs['all'] = list(search_bugs())
    LOG.debug('%d ironic bugs', len(ironic_bugs['all']))
    nova_bugs['all'] = list(search_nova_bugs())
    LOG.debug('%d nova bugs', len(nova_bugs['all']))

    for d in (ironic_bugs, nova_bugs):
        for status in ('New', 'Incomplete', 'In Progress'):
            d[status] = list(search_in_cache(d, status=status))
        for importance in ('High', 'Critical'):
            d[importance] = list(search_in_cache(
                d, importance=importance))

    ironic_undecided = search_in_cache(ironic_bugs,
                                       importance='Undecided',
                                       status=TRIAGED_STATUSES)

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

    stats = TEMPLATE.render(
        ironic_bugs=ironic_bugs,
        nova_bugs=nova_bugs,
        new_or_confirmed=new_or_confirmed,
        undecided=ironic_undecided,
        users=users,
        unassigned_in_progress=unassigned_in_progress,
    )
    return stats


TEMPLATE = u"""
{%- macro render_bug(bug) -%}
<li>{{ bug.status }} <a href="{{ bug.web_link }}">{{ bug.title }}</a><br>
created on {{ bug.date_created }}
{% if bug.assignee %}
assigned to <a href="https://launchpad.net/~{{ bug.assignee }}">
~{{ bug.assignee }}</a>
{% endif %}
{%- endmacro -%}

<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css">
<style>
h1 {text-align: center;}
</style>
<title>Ironic Bug Dashboard</title>
</head>
<body>
<div class="container">
<hr>

<h1>Stats</h1>

<p>Open: {{ ironic_bugs['all'] | length }}.
{{ ironic_bugs['New'] | length }} new,
{{ ironic_bugs['In Progress'] | length }} in progress,
{{ ironic_bugs['Critical'] | length }} critical,
{{ ironic_bugs['High'] | length }} high and
{{ ironic_bugs['Incomplete'] | length }} incomplete</p>

<p><a href="https://bugs.launchpad.net/nova/+bugs?field.tag=ironic">
Nova bugs with Ironic tag</a>: {{ nova_bugs['all'] | length }}.
{{ nova_bugs['New'] | length }} new,
{{ nova_bugs['Critical'] | length }} critical,
{{ nova_bugs['High'] | length }} high</p>

<h1>Attention Required</h1>

<h2>Undecided Importance</h2>
<p>Ironic bugs that have 'Undecided' importance.</p>
<ul>
{% for bug in undecided %}
{{ render_bug(bug) }}
{% endfor %}
</ul>

<h2>Unassigned In Progress</h2>
<p>Ironic bugs that have 'In Progress' status, but don't have an assignee.</p>
<ul>
{% for bug in unassigned_in_progress %}
{{ render_bug(bug) }}
{% endfor %}
</ul>

<hr>
<h1>Triaging Required</h1>

<p>Ironic and Nova bugs that have 'New' or 'Confirmed' status.</p>
<ul>
{% for bug in new_or_confirmed %}
{{ render_bug(bug) }}
{% endfor %}
</ul>

<h1>In Progress Bugs</h1>
{% for user, bugs in users | dictsort %}
<h3>{{ user }}</h3>
<ul>
{% for bug in bugs %}
{{ render_bug(bug) }}
{% endfor %}
</ul>
{% endfor %}

<hr>
<p><a href="https://github.com/dtantsur/ironic-bug-dashboard">
Source code, pull requests, suggestions
</a></p>
</div></body></html>
"""


TEMPLATE = jinja2.Template(TEMPLATE)


if __name__ == '__main__':
    try:
        debug = sys.argv[1] == '--debug'
    except IndexError:
        debug = False
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(
        logging.ERROR)

    app.run(debug=debug)
