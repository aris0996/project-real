import multiprocessing

# Binding
bind = 'unix:/run/sipandai.sock'  # Unix socket untuk komunikasi dengan Apache
# bind = '127.0.0.1:8000'  # Alternatif menggunakan TCP socket

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Process Naming
proc_name = 'sipandai'
pythonpath = '/path/to/your/app'

# Logging
accesslog = '/var/log/sipandai/access.log'
errorlog = '/var/log/sipandai/error.log'
loglevel = 'info'

# SSL (jika menggunakan HTTPS)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190 