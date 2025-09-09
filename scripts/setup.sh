#!/bin/bash

echo "Setting up Cybersecurity Compliance System..."

# Create necessary directories
mkdir -p ./blockchain/config/wallet
mkdir -p ./ai-engine/models
mkdir -p ./config

# Build and start services
docker-compose build
docker-compose up -d

# Wait for services to start
sleep 30

# Initialize blockchain network
echo "Initializing blockchain network..."
docker exec -it blockchain ./scripts/init-network.sh

# Load sample data
echo "Loading sample data..."
docker exec -it postgres psql -U admin -d compliance_db -f /docker-entrypoint-initdb.d/init.sql

echo "Setup completed! System is running."
echo "Frontend: http://localhost"
echo "Backend API: http://localhost:3000"
echo "Health check: http://localhost:3000/health"