#!/bin/bash

# Initialize Hyperledger Fabric network
./network.sh down
./network.sh up createChannel -c mychannel -ca
./network.sh deployCC -ccn compliance-contract -ccp ../chaincode/javascript -ccl javascript

# Register admin user
./scripts/registerUser.sh admin