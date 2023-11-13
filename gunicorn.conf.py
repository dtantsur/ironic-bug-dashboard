import multiprocessing

accesslog = "-"
bind = "0.0.0.0:8000"
proc_name = "ironic-bug-dashboard"
workers = multiprocessing.cpu_count() + 1
