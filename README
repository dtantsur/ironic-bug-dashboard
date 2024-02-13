This is a dashboard for tracking outstanding bugs in **Ironic**.

**Ironic** is one of the software components in OpenStack that fully manages baremetal infrastructure; it discovers bare-metal modes; catalogs them in a management database and manages the entire server lifecycle; from enrolling to provisioning, maintenance and decomissioning.

And **OpenStack** is an opensource cloud software project that is made up of a collection of software components that provide common services for cloud infrastructure.

## Setup
Before diving into the setup process, ensure that your Python version is `>=python3.11`.

### Creating a Virtual Environment
To keep your dependencies isolated, it's recommended to create a virtual environment. You can do this by running the following commands:

```bash
$ python3 -m venv env
$ source env/bin/activate  # For Unix/Linux
$ env\Scripts\activate      # For Windows
```

This will activate the virtual environment, providing a clean workspace for your project.

### Installing Dependencies
Once inside your virtual environment, you can install the required dependencies using pip:

```bash
$ pip install -r requirements.txt
```

This command will install all the necessary Python packages listed in the `requirements.txt` file.

## Usage
This is an AIOHTTP application and can be run as such.


### 🧪 Run in Development
For local testing use:

```
$ tox -erun
```

### 🚀 Run in Production
For actual production, a Dockerfile is provided that uses gunicorn internally:

```
$ podman build -t ironic-bug-dashboard .
$ podman run --name ironic-bug-dashboard --publish 8000:8000 ironic-bug-dashboard
```

## Features
Tracking outstanding bugs in Ironic for contributors, bug deputies/triagers.

## ❤️ How to Contribute
Contributions are welcomed and encouraged! 

This repo uses Github Issues and Github fork-then-PR workflow for development and here's how you can contribute:

1. Clone the repository and create a new branch for your changes:

```
$ git checkout https://github.com/dtantsur/ironic-bug-dashboard/ -b name_for_new_branch
```

2. Make your desired changes and ensure to test them thoroughly.

3. Submit a Pull Request with a detailed description of your changes. Your contribution will be reviewed by the project maintainers.

For information on how to contribute to ironic, see https://docs.openstack.org/ironic/latest/contributor

## ©️ License
This project is licensed under the ⚖️ [MIT License](https://github.com/dtantsur/ironic-bug-dashboard/?tab=MIT-1-ov-file).

Feel free to use and modify it according to the terms specified in the license.

## 🔗 Project Links
- OpenStack: https://www.openstack.org/
- Ironic: https://opendev.org/openstack/ironic/
- Ironic Bugs: https://bugs.launchpad.net/ironic/+bugs
