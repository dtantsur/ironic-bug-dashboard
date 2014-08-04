PYTHON?=python

run:
	@test -d .env || { echo "Run make env first"; exit 1; }
	.env/bin/python ironic_bug_dashboard.py

env:
	rm -rf .env
	virtualenv -p ${PYTHON} .env
	.env/bin/pip install requests Flask Flask-Cache

.PHONY: run env
