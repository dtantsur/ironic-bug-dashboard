#!/usr/bin/env python

import os


virtenv = os.environ['OPENSHIFT_PYTHON_DIR'] + '/virtenv/'
virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
try:
    exec(compile(open(virtualenv, 'rb').read(), virtualenv, 'exec'),
         dict(__file__=virtualenv))
except IOError:
    pass


from ironic_bug_dashboard import app as application  # noqa
