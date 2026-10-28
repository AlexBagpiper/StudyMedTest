#!/bin/sh

# Wait for database (no netcat required in slim image)
echo "Waiting for database..."
python - <<'PY'
import socket
import sys
import time

host, port = "db", 5432
for _ in range(120):
    try:
        with socket.create_connection((host, port), timeout=2):
            break
    except OSError:
        time.sleep(1)
else:
    sys.exit("database not ready after 120s")
PY
echo "Database is up!"

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Initialize database (create admin, etc.)
echo "Initializing database..."
python init_db.py

echo "Initialization complete!"
