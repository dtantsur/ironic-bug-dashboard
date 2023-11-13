import multiprocessing

accesslog = "-"
bind = "0.0.0.0:8000"
proc_name = "ironic-bug-dashboard"
workers = min(multiprocessing.cpu_count() + 1, 4)
worker_class = "aiohttp.GunicornWebWorker"
