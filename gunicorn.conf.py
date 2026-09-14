# Gunicorn Production Configuration for Security Dept System
import multiprocessing

bind = '0.0.0.0:7000'
backlog = 2048

# Workers & Concurrency
workers = 3
threads = 2
worker_class = 'gthread'
worker_connections = 1000
timeout = 60
keepalive = 5

# Memory management & recycling
max_requests = 1000
max_requests_jitter = 50

# Process naming
proc_name = 'security_dept_gunicorn'

# Logging
loglevel = 'info'
accesslog = '/home/tserver/security_dept/logs/gunicorn_access.log'
errorlog = '/home/tserver/security_dept/logs/gunicorn_error.log'
capture_output = True
enable_stdio_inheritance = True
