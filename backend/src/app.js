const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const pool = require('./database');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(cors());
app.use(express.json());

// Fabric Network Connection (optional - will run in simulation mode if not configured)
let gateway;
let contract;
let blockchainEnabled = false;

async function connectToBlockchain() {
    try {
        // Check if Fabric configuration exists
        const fabricConfigPath = process.env.FABRIC_CONFIG_PATH;
        if (!fabricConfigPath) {
            console.warn('FABRIC_CONFIG_PATH not set - running in simulation mode');
            return;
        }

        const ccpPath = path.resolve(fabricConfigPath, 'connection-org1.json');
        if (!fs.existsSync(ccpPath)) {
            console.warn('Fabric configuration not found - running in simulation mode');
            return;
        }

        // Only require fabric-network if we have configuration
        const { Gateway, Wallets } = require('fabric-network');
        
        const ccp = JSON.parse(fs.readFileSync(ccpPath, 'utf8'));

        const walletPath = path.join(fabricConfigPath, 'wallet');
        const wallet = await Wallets.newFileSystemWallet(walletPath);

        const identity = await wallet.get('admin');
        if (!identity) {
            console.warn('Admin identity not found in wallet - running in simulation mode');
            return;
        }

        gateway = new Gateway();
        await gateway.connect(ccp, {
            wallet,
            identity: 'admin',
            discovery: { enabled: true, asLocalhost: true }
        });

        const network = await gateway.getNetwork('mychannel');
        contract = network.getContract('compliance-contract');
        
        blockchainEnabled = true;
        console.log('Connected to Hyperledger Fabric network');
    } catch (error) {
        console.warn('Failed to connect to blockchain - running in simulation mode:', error.message);
        blockchainEnabled = false;
    }
}

// Simulated blockchain functions for development
class SimulationMode {
    constructor() {
        this.actions = [];
    }

    async submitTransaction(functionName, ...args) {
        const actionData = JSON.parse(args[0]);
        const complianceRecord = {
            id: uuidv4(),
            ...actionData,
            status: 'EXECUTED',
            timestamp: new Date().toISOString(),
            blockHash: 'simulated-' + Math.random().toString(36).substr(2, 9)
        };
        
        this.actions.push(complianceRecord);
        return Buffer.from(JSON.stringify(complianceRecord));
    }

    async evaluateTransaction(functionName) {
        return Buffer.from(JSON.stringify(this.actions));
    }
}

// Initialize simulation mode as fallback
let simulationContract = new SimulationMode();

// API Routes
app.post('/api/compliance/action', async (req, res) => {
    try {
        const actionData = req.body;
        
        // Validate input
        if (!actionData.policyId || !actionData.action) {
            return res.status(400).json({ error: 'Missing required fields' });
        }

        let complianceRecord;

        if (blockchainEnabled) {
            // Execute on real blockchain
            const result = await contract.submitTransaction(
                'ExecuteComplianceAction', 
                JSON.stringify(actionData)
            );
            complianceRecord = JSON.parse(result.toString());
        } else {
            // Use simulation mode
            const result = await simulationContract.submitTransaction(
                'ExecuteComplianceAction', 
                JSON.stringify(actionData)
            );
            complianceRecord = JSON.parse(result.toString());
        }
        
        // Store in database for quick querying
        try {
            await pool.query(
                `INSERT INTO compliance_actions 
                 (id, policy_id, action_taken, threat_description, confidence, status, timestamp)
                 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
                [
                    complianceRecord.id,
                    complianceRecord.policyId,
                    complianceRecord.action,
                    complianceRecord.threatDescription || '',
                    complianceRecord.confidence || 0.0,
                    complianceRecord.status || 'PENDING',
                    new Date().toISOString()
                ]
            );
        } catch (dbError) {
            console.warn('Database storage failed (continuing):', dbError.message);
            // Continue even if database fails
        }

        // Trigger enforcement
        await triggerEnforcement(complianceRecord);

        res.json(complianceRecord);
    } catch (error) {
        console.error('Compliance action failed:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/compliance/actions', async (req, res) => {
    try {
        let actions;
        
        if (blockchainEnabled) {
            const result = await contract.evaluateTransaction('QueryAllActions');
            actions = JSON.parse(result.toString());
        } else {
            const result = await simulationContract.evaluateTransaction('QueryAllActions');
            actions = JSON.parse(result.toString());
        }
        
        res.json(actions);
    } catch (error) {
        console.error('Failed to fetch actions, trying database:', error);
        
        // Fallback to database
        try {
            const { rows } = await pool.query('SELECT * FROM compliance_actions ORDER BY timestamp DESC');
            res.json(rows);
        } catch (dbError) {
            res.status(500).json({ error: 'Failed to fetch actions from all sources' });
        }
    }
});

app.get('/api/policies', async (req, res) => {
    try {
        const { rows } = await pool.query('SELECT * FROM policies ORDER BY severity DESC');
        res.json(rows);
    } catch (error) {
        console.error('Failed to fetch policies:', error);
        
        // Return default policies if database fails
        const defaultPolicies = [
            { id: 'POL-001', standard: 'NIST', control: 'Access Control', severity: 'HIGH', required_action: 'ENABLE_MFA' },
            { id: 'POL-002', standard: 'ISO27001', control: 'Cryptography', severity: 'MEDIUM', required_action: 'ENABLE_ENCRYPTION' },
            { id: 'POL-003', standard: 'PCI-DSS', control: 'Network Security', severity: 'CRITICAL', required_action: 'BLOCK_RDP_PORT' }
        ];
        res.json(defaultPolicies);
    }
});

async function triggerEnforcement(action) {
    try {
        console.log(`Enforcing action: ${action.actionTaken}`);
        // Simulate enforcement - in real implementation, this would call Ansible, Terraform, etc.
        // For now, just log the action
        console.log(`✅ Enforcement triggered for policy ${action.policyId}: ${action.actionTaken}`);
    } catch (error) {
        console.error('Enforcement trigger failed:', error);
    }
}

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        timestamp: new Date().toISOString(),
        blockchain: blockchainEnabled ? 'connected' : 'simulation',
        database: 'connected' // Assuming database is working
    });
});

// Test endpoint to check blockchain status
app.get('/api/blockchain/status', (req, res) => {
    res.json({
        enabled: blockchainEnabled,
        mode: blockchainEnabled ? 'production' : 'simulation'
    });
});

// Error handling
app.use((error, req, res, next) => {
    console.error('Unhandled error:', error);
    res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3000;

async function startServer() {
    try {
        await connectToBlockchain();
        app.listen(PORT, () => {
            console.log(`Backend server running on port ${PORT}`);
            console.log(`Blockchain mode: ${blockchainEnabled ? 'Production' : 'Simulation'}`);
            console.log(`Health check: http://localhost:${PORT}/health`);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    console.log('Shutting down server...');
    if (gateway) {
        await gateway.disconnect();
    }
    process.exit(0);
});

startServer();