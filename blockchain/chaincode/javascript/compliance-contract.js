const { Contract } = require('fabric-contract-api');
const { v4: uuidv4 } = require('uuid');

class ComplianceContract extends Contract {
    
    async InitLedger(ctx) {
        // Initialize baseline policies
        const policies = [
            {
                id: 'pol-nist-ac-1',
                standard: 'NIST',
                control: 'AC-1',
                description: 'Limit system access to authorized users.',
                requiredAction: 'ACCESS_CONTROL',
                severity: 'HIGH',
                docType: 'policy'
            },
            {
                id: 'pol-cis-2.1',
                standard: 'CIS',
                control: 'CIS-2.1',
                description: 'Disable SMBv1 protocol.',
                requiredAction: 'DISABLE_SMBv1',
                severity: 'CRITICAL',
                docType: 'policy'
            }
        ];

        for (const policy of policies) {
            await ctx.stub.putState(policy.id, Buffer.from(JSON.stringify(policy)));
        }
        
        console.log('Ledger initialized with default policies');
    }

    async CreatePolicy(ctx, policyId, standard, control, description, requiredAction, severity) {
        const exists = await this.PolicyExists(ctx, policyId);
        if (exists) {
            throw new Error(`Policy ${policyId} already exists`);
        }

        const policy = {
            id: policyId,
            standard,
            control,
            description,
            requiredAction,
            severity,
            docType: 'policy'
        };

        await ctx.stub.putState(policyId, Buffer.from(JSON.stringify(policy)));
        return JSON.stringify(policy);
    }

    async PolicyExists(ctx, policyId) {
        const policyJSON = await ctx.stub.getState(policyId);
        return policyJSON && policyJSON.length > 0;
    }

    async GetPolicy(ctx, policyId) {
        const policyJSON = await ctx.stub.getState(policyId);
        if (!policyJSON || policyJSON.length === 0) {
            throw new Error(`Policy ${policyId} does not exist`);
        }
        return policyJSON.toString();
    }

    async GetAllPolicies(ctx) {
        const iterator = await ctx.stub.getStateByRange('', '');
        const results = [];
        
        let res = await iterator.next();
        while (!res.done) {
            if (res.value && res.value.value.toString()) {
                const record = JSON.parse(res.value.value.toString('utf8'));
                if (record.docType === 'policy' || record.id.startsWith('pol-')) {
                    results.push(record);
                }
            }
            res = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(results);
    }

    async ExecuteComplianceAction(ctx, actionDataJSON) {
        const actionData = JSON.parse(actionDataJSON);
        const actionId = uuidv4();
        
        const complianceRecord = {
            id: actionId,
            timestamp: new Date().toISOString(),
            policyId: actionData.policyId,
            threatDescription: actionData.threatDescription,
            actionTaken: actionData.action,
            status: 'EXECUTED',
            confidence: actionData.confidence,
            targetEndpoints: actionData.targetEndpoints,
            docType: 'complianceAction'
        };

        await ctx.stub.putState(actionId, Buffer.from(JSON.stringify(complianceRecord)));
        
        ctx.stub.setEvent('ComplianceActionExecuted', 
            Buffer.from(JSON.stringify(complianceRecord)));
        
        return JSON.stringify(complianceRecord);
    }

    // Accept executeDecision(payloadJson)
    async executeDecision(ctx, payload) {
        const obj = JSON.parse(payload);
        const decision = obj.decision;
        const metadata = obj.metadata;
        
        // Example: write a ledger entry
        const txId = ctx.stub.getTxID();
        const entry = {
            txId,
            decision,
            metadata,
            timestamp: new Date().toISOString(),
            docType: 'decision'
        };
        
        // Save to ledger for auditing
        await ctx.stub.putState('audit_'+txId, Buffer.from(JSON.stringify(entry)));
        
        // Optionally emit events for external enforcement engine
        await ctx.stub.setEvent('DecisionExecuted', Buffer.from(JSON.stringify(entry)));
        
        return JSON.stringify({txId, status:'SUCCESS'});
    }

    async QueryAllActions(ctx) {
        const iterator = await ctx.stub.getStateByRange('', '');
        const results = [];
        
        let res = await iterator.next();
        while (!res.done) {
            if (res.value && res.value.value.toString()) {
                const record = JSON.parse(res.value.value.toString('utf8'));
                if (record.docType === 'complianceAction') {
                    results.push(record);
                }
            }
            res = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(results);
    }

    async QueryAction(ctx, actionId) {
        const actionJSON = await ctx.stub.getState(actionId);
        if (!actionJSON || actionJSON.length === 0) {
            throw new Error(`Action ${actionId} does not exist`);
        }
        return actionJSON.toString();
    }

    async QueryAllDecisions(ctx) {
        const iterator = await ctx.stub.getStateByRange('', '');
        const results = [];
        
        let res = await iterator.next();
        while (!res.done) {
            if (res.value && res.value.value.toString()) {
                const record = JSON.parse(res.value.value.toString('utf8'));
                if (record.docType === 'decision') {
                    results.push(record);
                }
            }
            res = await iterator.next();
        }
        
        await iterator.close();
        return JSON.stringify(results);
    }

    async QueryDecision(ctx, txId) {
        const decisionJSON = await ctx.stub.getState('audit_'+txId);
        if (!decisionJSON || decisionJSON.length === 0) {
            throw new Error(`Decision with txId ${txId} does not exist`);
        }
        return decisionJSON.toString();
    }
}

module.exports = ComplianceContract;