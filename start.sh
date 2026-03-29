#!/bin/bash

# Exit on any error
set -e
export PYTHONPATH="/app:${PYTHONPATH}"
uv run app/database.py

echo "Running database migrations..."
uv run alembic upgrade head

echo "Inserting documentation into database..."
uv run fastapi run app/main.py --port 8000 --host 0.0.0.0