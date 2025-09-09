#!/bin/bash

set -e

echo "Initializing Hyperledger Fabric network..."

# Generate cryptographic material
if [ ! -d "../config/crypto-config" ]; then
    echo "Generating crypto material..."
    ./generate-crypto.sh
fi

# Generate genesis block
if [ ! -f "../config/genesis.block" ]; then
    echo "Generating genesis block..."
    ../bin/configtxgen -profile OneOrgOrdererGenesis -channelID system-channel -outputBlock ../config/genesis.block -configPath ../config
fi

# Create channel configuration transaction
if [ ! -f "../config/mychannel.tx" ]; then
    echo "Creating channel transaction..."
    ../bin/configtxgen -profile OneOrgChannel -outputCreateChannelTx ../config/mychannel.tx -channelID mychannel -configPath ../config
fi

# Create anchor peer transaction
if [ ! -f "../config/Org1MSPanchors.tx" ]; then
    echo "Creating anchor peer transaction..."
    ../bin/configtxgen -profile OneOrgChannel -outputAnchorPeersUpdate ../config/Org1MSPanchors.tx -channelID mychannel -asOrg Org1MSP -configPath ../config
fi

# Start the network
echo "Starting network components..."
docker-compose up -d orderer.example.com peer0.org1.example.com

# Wait for components to start
sleep 10

# Create channel
echo "Creating channel..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt" \
  cli peer channel create \
  -o orderer.example.com:7050 \
  -c mychannel \
  -f /var/hyperledger/config/mychannel.tx \
  --tls \
  --cafile /var/hyperledger/config/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt

# Join peer to channel
echo "Joining peer to channel..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt" \
  cli peer channel join \
  -b mychannel.block \
  --tls \
  --cafile /var/hyperledger/config/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt

# Update anchor peer
echo "Updating anchor peer..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/crypto-config/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt" \
  cli peer channel update \
  -o orderer.example.com:7050 \
  -c mychannel \
  -f /var/hyperledger/config/Org1MSPanchors.tx \
  --tls \
  --cafile /var/hyperledger/config/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/tls/ca.crt

echo "Network initialized successfully!"