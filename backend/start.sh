#!/bin/sh
set -e

# Use `heads` instead of `head` so deploys don't crash if the environment
# temporarily contains multiple Alembic heads before a merge migration lands.
alembic upgrade heads
python /app/app/db/seed.py

uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-80}"
