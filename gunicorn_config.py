import multiprocessing

# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/configure.html#configuration-file

# Server socket
bind = "0.0.0.0:4242"

# Worker processes
# A common formula is (2 x num_cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # Use 'gevent' or 'eventlet' for async if needed
threads = 2

# Timeouts
timeout = 120  # 2 minutes
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "integracao_stripe_api"