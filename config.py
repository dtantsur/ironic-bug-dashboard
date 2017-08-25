import os


workers = int(os.environ.get('GUNICORN_PROCESSES', '2'))
threads = int(os.environ.get('GUNICORN_THREADS', '1'))
worker_class = 'eventlet'

forwarded_allow_ips = '*'
secure_scheme_headers = {'X-Forwarded-Proto': 'https'}
