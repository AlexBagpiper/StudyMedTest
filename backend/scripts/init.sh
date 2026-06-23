#!/bin/sh

# Wait for database
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is up!"

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Initialize database (create admin, etc.)
echo "Initializing database..."
python init_db.py

echo "Initialization complete!"
