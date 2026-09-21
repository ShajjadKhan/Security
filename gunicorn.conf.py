# Gunicorn Production Configuration for Security Dept System
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8001')
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
accesslog = str(LOGS_DIR / 'gunicorn_access.log')
errorlog = str(LOGS_DIR / 'gunicorn_error.log')
capture_output = True
enable_stdio_inheritance = True
