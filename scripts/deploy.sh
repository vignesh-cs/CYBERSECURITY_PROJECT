#!/bin/bash

set -e

echo "🚀 Deploying Cybersecurity Compliance System..."
echo "=============================================="

# Load environment variables
if [ -f "./config/.env" ]; then
    export $(cat ./config/.env | grep -v '#' | awk '/=/ {print $1}')
fi

# Create network if it doesn't exist
if ! docker network ls | grep -q "compliance-net"; then
    docker network create compliance-net
fi

# Build and start services
echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Initialize database
echo "Initializing database..."
docker exec -it postgres psql -U admin -d compliance_db -f /docker-entrypoint-initdb.d/init.sql

# Initialize blockchain network
echo "Initializing blockchain network..."
docker exec -it blockchain /bin/bash -c "cd /var/hyperledger/scripts && ./init-network.sh"

# Deploy chaincode
echo "Deploying chaincode..."
docker exec -it blockchain /bin/bash -c "cd /var/hyperledger/scripts && ./deployCC.sh"

# Register admin user
echo "Registering admin user..."
docker exec -it blockchain /bin/bash -c "cd /var/hyperledger/scripts && ./registerUser.sh admin"

# Load sample data
echo "Loading sample data..."
docker exec -it postgres psql -U admin -d compliance_db -c "
INSERT INTO compliance_actions (policy_id, action_taken, threat_description, confidence, status) 
VALUES 
('pol-cis-2.1', 'DISABLE_SMBv1', 'Ransomware threat exploiting SMBv1', 0.95, 'EXECUTED'),
('pol-nist-sc-7', 'UPDATE_FIREWALL', 'Port scanning detected', 0.88, 'EXECUTED'),
('pol-nist-si-3', 'UPDATE_ANTIVIRUS', 'Malware signature update required', 0.92, 'EXECUTED');
"

echo "✅ Deployment completed successfully!"
echo ""
echo "📊 Services:"
echo "   Frontend: http://localhost"
echo "   Backend API: http://localhost:3000"
echo "   Health check: http://localhost:3000/health"
echo "   Blockchain Explorer: http://localhost:8080 (if configured)"
echo ""
echo "🔧 Next steps:"
echo "   1. Access the web interface"
echo "   2. Configure your endpoints in the database"
echo "   3. Set up CTI API keys in config/.env"
echo "   4. Monitor compliance actions in the dashboard"