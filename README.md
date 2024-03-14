# Ironic Bug Dashbaord

This is an AIOHTTP dashboard application for tracking outstanding bugs in Launchpad projects.

## Setup & Local Testing
- Create a <project_name>.json file in the `ironic_bug_dashboard/configs/` directory.

E.g:

`ironic_bug_dashboard/configs/ironic.json`:

```
{
    "projects": [
        //project(s),
    ],
    "tagged_projects": [
        {
            "project_name": "nova",
            "tags": "ironic"
        },
        ...
    ],
    "priority_required_statuses": ["New", "In Progress", "Triaged", "Confirmed"],
    "status_priorities": {
        "In Progress": -10,
        "Triaged": -5,
        "Confirmed": -5
    }
  }
```

- Run Locally

The `tox -erun` command installs and manages dependencings and also spins up the dashboard for local testing use.

```bash
$ tox -erun
```

## 🚀 Run in Production
For actual production, a Dockerfile is provided that uses gunicorn internally:

```
$ podman build -t ironic-bug-dashboard .
$ podman run --name ironic-bug-dashboard --publish 8000:8000 ironic-bug-dashboard
```

## Features
Tracking outstanding bugs for contributors, bug deputies/triagers.

## ❤️ How to Contribute
Contributions are welcomed and encouraged!

This repo uses Github Issues and Github fork-then-PR workflow for development.

## ©️ License
This project is licensed under the ⚖️ [MIT License](https://github.com/dtantsur/ironic-bug-dashboard/blob/master/LICENSE).

Feel free to use and modify it according to the terms specified in the license.
