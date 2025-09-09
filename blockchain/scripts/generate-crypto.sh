#!/bin/bash

set -e

echo "Generating cryptographic materials..."

# Create crypto-config directory
mkdir -p ../config/crypto-config

# Generate crypto materials using cryptogen
../bin/cryptogen generate --config=../config/crypto-config.yaml --output=../config/crypto-config

echo "Cryptographic materials generated successfully!"
echo "Files created in: ../config/crypto-config/"