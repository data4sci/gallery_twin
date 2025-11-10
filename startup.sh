#!/bin/bash
set -e

echo "Starting application..."

# Ensure database directory exists
mkdir -p /home/site/wwwroot/db

# Update DATABASE_URL to point to persistent storage
export DATABASE_URL="sqlite+aiosqlite:////home/site/wwwroot/db/gallery.db"

# Start the application
echo "Starting uvicorn..."
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
