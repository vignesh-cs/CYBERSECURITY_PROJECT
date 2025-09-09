#!/bin/bash

set -e

echo "Initializing database..."

# Wait for PostgreSQL to be ready
until pg_isready -h postgres -U admin -d compliance_db; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

# Run initialization script
psql -h postgres -U admin -d compliance_db -f /docker-entrypoint-initdb.d/init.sql

echo "Database initialized successfully!"