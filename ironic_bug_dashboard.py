import logging
import sys

from flask import Flask

from simple_lp import search_bugs, search_nova_bugs, OPEN_STATUSES


LOG = logging.getLogger(__name__)


HEADER = unicode("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
<link rel="stylesheet"
href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css">
<title>Ironic Bug Dashboard</title>
</head>
<body>
<div class="container">""")


STATS_TEMPLATE = unicode(
    "<h1>Stats</h1>"
    "<p>Open: {total}. {new} new, {progress} in progress, "
    "{critical} critical, {high} high and {incomplete} incomplete</p>"
    "<p><a href=\"https://bugs.launchpad.net/nova/+bugs?field.tag=ironic\">"
    "Nova bugs with Ironic tag</a>: {nova_total}. {nova_new} new, "
    "{nova_critical} critical, {nova_high} high</p>"
    "<h2>Undecided Importance</h2>"
    "<p>Ironic bugs that have 'Undecided' importance, but have status "
    "other than 'New' or 'Incomplete'.</p>"
    "<ul>{undecided_bugs_html}</ul>"
    "<h2>Unassigned In Progress</h2>"
    "<p>Ironic bugs that have 'In Progress' status, but don't have "
    "an assignee.</p>"
    "<ul>{unassigned_in_progress}</ul>"
    "<h2>New and Confirmed Bugs</h2>"
    "<p>Ironic and Nova bugs that have 'New' or 'Confirmed' status.</p>"
    "<ul>{new_bugs_html}</ul>"
    "<h2>In Progress Bugs</h2>"
    "{assigned_bugs_html}"
)


FOOTER = unicode(
    "<br><br>"  # Being a cool frontend developer
    "<p><a href=\"https://github.com/dtantsur/ironic-bug-dashboard\">"
    "Source code, pull requests, suggestions"
    "</a></p>"
    "</div></body></html>"
)


STATS_TEMPLATE = HEADER + STATS_TEMPLATE + FOOTER


BUG_TEMPLATE = unicode(
    "<li>"
    "{bug[status]} <a href=\"{bug[web_link]}\">{bug[title]}</a><br>"
    "created on {bug[date_created]}"
)


ASSIGNEE_TEMPLATE = unicode(
    u" assigned to "
    u"<a href=\"https://launchpad.net/~{assignee}\">~{assignee}</a>"
)


app = Flask(__name__)


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
        assignee = (bug['assignee_link'].split('~')[1]
                    if bug['assignee_link'] is not None else '')
        if assignee:
            users.setdefault(assignee, []).append(bug)
        else:
            unassigned_in_progress.append(bug)
    assigned_bugs_html = ''.join(
        u'<h3>{assignee}</h3><ul>{bugs}</ul>'.format(
            assignee=assignee,
            bugs=format_bugs(bugs, False)
        )
        for (assignee, bugs) in sorted(users.items(), key=lambda x: x[1]))

    stats = STATS_TEMPLATE.format(
        total=len(ironic_bugs['all']),
        new=len(ironic_bugs['New']),
        progress=len(ironic_bugs['In Progress']),
        critical=len(ironic_bugs['Critical']),
        high=len(ironic_bugs['High']),
        incomplete=len(ironic_bugs['Incomplete']),
        nova_new=len(nova_bugs['New']),
        nova_total=len(nova_bugs['all']),
        nova_critical=len(nova_bugs['Critical']),
        nova_high=len(nova_bugs['High']),
        new_bugs_html=format_bugs(new_or_confirmed),
        undecided_bugs_html=format_bugs(ironic_undecided),
        assigned_bugs_html=assigned_bugs_html,
        unassigned_in_progress=format_bugs(unassigned_in_progress),
    )
    return stats


if __name__ == '__main__':
    try:
        debug = sys.argv[1] == '--debug'
    except IndexError:
        debug = False
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(
        logging.ERROR)

    app.run(debug=debug)
