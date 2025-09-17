#!/bin/bash
set -e

echo "Waiting for database to be ready..."

# Wait for database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "db" -U "empires" -d "empires_db" -c '\q'; do
  >&2 echo "Database is unavailable - sleeping"
  sleep 1
done

>&2 echo "Database is up - executing command"

# Initialize database
python app/init_db.py

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload