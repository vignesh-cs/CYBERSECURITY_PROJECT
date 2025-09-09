#!/bin/bash

set -e

CHAINCODE_NAME=${1:-compliance-contract}
CHAINCODE_VERSION=${2:-1.0}
CHAINCODE_SEQUENCE=${3:-1}
CHAINCODE_PATH=${4:-/opt/gopath/src/github.com/chaincode/javascript}

echo "Deploying chaincode $CHAINCODE_NAME version $CHAINCODE_VERSION..."

# Package chaincode
echo "Packaging chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode package ${CHAINCODE_NAME}.tar.gz \
  --path $CHAINCODE_PATH \
  --lang node \
  --label ${CHAINCODE_NAME}_${CHAINCODE_VERSION}

# Install chaincode
echo "Installing chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode install ${CHAINCODE_NAME}.tar.gz \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt

# Query installed chaincode
echo "Querying installed chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode queryinstalled

# Get package ID
PACKAGE_ID=$(docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode queryinstalled | grep -o "${CHAINCODE_NAME}.*" | cut -d" " -f3 | cut -d"," -f1)

echo "Package ID: $PACKAGE_ID"

# Approve chaincode for organization
echo "Approving chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode approveformyorg \
  -o orderer.example.com:7050 \
  --channelID mychannel \
  --name $CHAINCODE_NAME \
  --version $CHAINCODE_VERSION \
  --package-id $PACKAGE_ID \
  --sequence $CHAINCODE_SEQUENCE \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt \
  --waitForEvent

# Check commit readiness
echo "Checking commit readiness..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode checkcommitreadiness \
  --channelID mychannel \
  --name $CHAINCODE_NAME \
  --version $CHAINCODE_VERSION \
  --sequence $CHAINCODE_SEQUENCE \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt

# Commit chaincode definition
echo "Committing chaincode definition..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode commit \
  -o orderer.example.com:7050 \
  --channelID mychannel \
  --name $CHAINCODE_NAME \
  --version $CHAINCODE_VERSION \
  --sequence $CHAINCODE_SEQUENCE \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt \
  --waitForEvent

# Query committed chaincode
echo "Querying committed chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer lifecycle chaincode querycommitted \
  --channelID mychannel \
  --name $CHAINCODE_NAME \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt

# Initialize chaincode
echo "Initializing chaincode..."
docker exec -e "CORE_PEER_LOCALMSPID=Org1MSP" \
  -e "CORE_PEER_MSPCONFIGPATH=/var/hyperledger/config/msp" \
  -e "CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/config/tls/ca.crt" \
  cli peer chaincode invoke \
  -o orderer.example.com:7050 \
  -C mychannel \
  -n $CHAINCODE_NAME \
  -c '{"function":"InitLedger","Args":[]}' \
  --tls \
  --cafile /var/hyperledger/config/tls/ca.crt \
  --waitForEvent

echo "Chaincode $CHAINCODE_NAME deployed successfully!"