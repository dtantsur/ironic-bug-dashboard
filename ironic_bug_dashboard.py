import sys

from flask import Flask
from flask.ext.cache import Cache

from simple_lp import search_bugs, OPEN_STATUSES


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
    "<h2>Unassigned In Progess</h2>"
    "<p>Ironic bugs that have 'In Progress' status, but don't have "
    "an assignee.</p>"
    "<ul>{unassigned_in_progress}</ul>"
    "<h2>New and Confirmed Bugs</h2>"
    "<p>Ironic and Nova bugs that have 'New' or 'Confirmed' status.</p>"
    "<ul>{new_bugs_html}</ul>"
    "<h2>In Progress Bugs</h2>"
    "{assigned_bugs_html}"
    "<br><br>"  # Being a cool frontend developer
    "<a href=\"https://github.com/divius/ironic-bug-dashboard\">"
    "Source code, pull requests, suggestions"
    "</a>"
)


FOOTER = unicode("</body></html>")


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
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


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


def search_nova_bugs(**conditions):
    conditions['project_names'] = ('nova',)
    conditions['tags'] = 'ironic'
    return search_bugs(**conditions)


@app.route("/")
@cache.cached(timeout=60)
def index():
    new_bugs = search_bugs(status='New')
    undecided_bugs = search_bugs(importance='Undecided',
                                 status=OPEN_STATUSES -
                                 set(['New', 'Incomplete']))
    in_progress_bugs = search_bugs(status='In Progress')

    nova_new = search_nova_bugs(status='New')
    nova_all = search_nova_bugs()
    nova_high = search_nova_bugs(importance='High')
    nova_critical = search_nova_bugs(importance='Critical')

    new_or_confirmed = (list(search_bugs(status=['New', 'Confirmed'])) +
                        list(search_nova_bugs(status=['New', 'Confirmed'])))
    new_or_confirmed.sort(key=lambda b: (b['status'] != 'New',
                                         b['date_created']))

    users = {}
    unassigned_in_progress = []
    for bug in in_progress_bugs:
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
        total=len(search_bugs()),
        new=len(new_bugs),
        progress=len(in_progress_bugs),
        critical=len(search_bugs(importance='Critical')),
        high=len(search_bugs(importance='High')),
        incomplete=len(search_bugs(status='Incomplete')),
        nova_new=len(nova_new),
        nova_total=len(nova_all),
        nova_critical=len(nova_critical),
        nova_high=len(nova_high),
        new_bugs_html=format_bugs(new_or_confirmed),
        undecided_bugs_html=format_bugs(undecided_bugs),
        assigned_bugs_html=assigned_bugs_html,
        unassigned_in_progress=format_bugs(unassigned_in_progress),
    )
    return stats


if __name__ == '__main__':
    try:
        debug = sys.argv[1] == '--debug'
    except IndexError:
        debug = False
    app.run(debug=debug)
