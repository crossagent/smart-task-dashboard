#!/bin/bash
set -e

# Hub Entrypoint
# This script manages the internal PostgreSQL service and initialization logic.
# It ensures that dependencies are synced and the database schema is ready before
# starting the application server.

# 1. Sync Dependencies
# We do this at runtime to support local development volume mounts directly.
echo "Syncing dependencies with uv..."
uv sync

# 2. Start PostgreSQL
# The data directory is persistent via Docker volumes.
export PGDATA=/var/lib/postgresql/data
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Initializing fresh PostgreSQL data directory..."
    su postgres -c "initdb -D $PGDATA"
fi

# Ensure pg_hba.conf allows all connections (necessary for host-to-container testing)
echo "host all all 0.0.0.0/0 trust" >> "$PGDATA/pg_hba.conf"
# Also ensure postgresql.conf listens on all addresses
echo "listen_addresses = '*'" >> "$PGDATA/postgresql.conf"

echo "Starting PostgreSQL 17 service..."
# Use pg_ctl to start in background, but log to stdout for visibility if needed
su postgres -c "pg_ctl -D $PGDATA -l /var/log/postgresql/postgresql.log start"

# 3. Wait for PostgreSQL to be READY
echo "Waiting for PostgreSQL to be healthy..."
MAX_WAIT=30
COUNT=0
until su postgres -c "pg_isready" > /dev/null 2>&1 || [ $COUNT -eq $MAX_WAIT ]; do
    sleep 1
    COUNT=$((COUNT + 1))
done

if [ $COUNT -eq $MAX_WAIT ]; then
    echo "ERROR: PostgreSQL failed to start within $MAX_WAIT seconds."
    exit 1
fi

# 4. Master Database initialization
# We run the master SQL script which handles Role/DB/Schema creation safely.
if [ -f "/app/src/init_all.sql" ]; then
    echo "Initializing Hub Database: Executing master script (/app/src/init_all.sql)..."
    su postgres -c "psql -f /app/src/init_all.sql"
    echo "Hub Database: Initialization complete."
else
    echo "Warning: /app/src/init_all.sql not found. Skipping SQL initialization."
fi

# 5. Start Application
echo "Core Hub: Starting service [$@]"
exec "$@"
