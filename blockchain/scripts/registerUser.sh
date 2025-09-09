#!/bin/bash

set -e

USERNAME=${1:-admin}

echo "Registering user $USERNAME..."

# Check if user already exists in wallet
if [ -d "../config/wallet/$USERNAME" ]; then
    echo "User $USERNAME already exists in wallet"
    exit 0
fi

# Register user
docker exec -e "FABRIC_CA_CLIENT_HOME=/var/hyperledger/config" \
  cli fabric-ca-client register \
  --id.name $USERNAME \
  --id.secret password \
  --id.type client \
  --id.affiliation org1 \
  --id.attrs 'hf.Revoker=true,admin=true:ecert' \
  --tls.certfiles /var/hyperledger/config/tls/ca.crt

# Enroll user
docker exec -e "FABRIC_CA_CLIENT_HOME=/var/hyperledger/config" \
  cli fabric-ca-client enroll \
  -u https://$USERNAME:password@ca.org1.example.com:7054 \
  --caname ca-org1 \
  -M /var/hyperledger/config/wallet/$USERNAME \
  --tls.certfiles /var/hyperledger/config/tls/ca.crt

echo "User $USERNAME registered successfully!"