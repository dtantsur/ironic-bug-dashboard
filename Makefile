run:
	@test -d .env || { echo "Run make env first"; exit 1; }
	.env/bin/python ironic_bug_dashboard.py

env:
	rm -rf .env
	virtualenv .env
	.env/bin/pip install --allow-all-external --allow-unverified lazr.authentication \
		Flask launchpadlib pyxdg

.PHONY: run env
