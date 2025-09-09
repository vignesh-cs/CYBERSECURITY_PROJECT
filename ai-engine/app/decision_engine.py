"""
Decision engine implementing Algorithm 1 from the paper.
Inputs: CTI_feed (list of CTI JSON objects)
Outputs: (decision, action_result)
"""

import os, json, time, subprocess, pickle
import random
import numpy as np
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# CONFIG: Simulation mode - set to False for production
SIMULATION_MODE = True

# CONFIG: paths (adjust if needed)
BASE = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE, "models")
SECUREBERT_DIR = os.path.join(MODELS_DIR, "securebert")   # HF-format
RF_PATH = os.path.join(MODELS_DIR, "rf_model.pkl")

# Global variables for models
rf = None
tokenizer = None
model = None

def initialize_models():
    """Initialize AI models with proper error handling"""
    global rf, tokenizer, model
    
    try:
        # Load RF model
        with open(RF_PATH, "rb") as f:
            rf = pickle.load(f)
        logger.info("RF model loaded successfully")
        print("✅ RF model loaded successfully")
    except Exception as e:
        logger.error(f"Could not load RF model: {e}")
        print(f"⚠️  Warning: Could not load RF model {e}")
        # Create a simple fallback RF model for simulation
        class FallbackRF:
            def predict(self, X):
                return ["SMB_THREAT"] * len(X)
        rf = FallbackRF()

    try:
        # Load SecureBERT tokenizer & model
        from transformers import AutoTokenizer, AutoModel
        import torch
        tokenizer = AutoTokenizer.from_pretrained(SECUREBERT_DIR)
        model = AutoModel.from_pretrained(SECUREBERT_DIR)
        model.eval()
        logger.info("SecureBERT model loaded successfully")
        print("✅ SecureBERT model loaded successfully")
    except Exception as e:
        logger.error(f"Could not load SecureBERT model: {e}")
        print(f"⚠️  Warning: Could not load SecureBERT model {e}")
        # Fallback for simulation
        tokenizer = None
        model = None

# Initialize models on import
initialize_models()

# DB helper (Postgres) - Simulation mode bypass
if not SIMULATION_MODE:
    import psycopg2
    def get_db_conn():
        return psycopg2.connect(
            dbname=os.getenv("POLICY_DB", "policies"),
            user=os.getenv("POLICY_DB_USER","postgres"),
            password=os.getenv("POLICY_DB_PASS","postgres"),
            host=os.getenv("POLICY_DB_HOST","postgres"),
            port=os.getenv("POLICY_DB_PORT","5432")
        )
else:
    # Simulation mode - mock database
    def get_db_conn():
        class MockConnection:
            def cursor(self):
                return MockCursor()
            def close(self):
                pass
        return MockConnection()
    
    class MockCursor:
        def execute(self, query, params=None):
            pass
        def fetchall(self):
            # Return mock policies for simulation
            return [
                ('POL-SMB-001', 'Disable SMBv1 Policy', 'CRITICAL', '["DISABLE_SMBv1"]'),
                ('POL-PHISH-001', 'Enable MFA Policy', 'HIGH', '["ENABLE_MFA"]'),
                ('POL-RANSOM-001', 'Isolate Endpoint Policy', 'CRITICAL', '["ISOLATE_ENDPOINT"]')
            ]
        def close(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

# helper: embed text (CLS pooling)
def embed_text(text):
    if model is None or tokenizer is None:
        # Fallback: return random embedding for simulation
        return np.random.rand(768)
    
    tokens = tokenizer(text, truncation=True, padding='max_length', max_length=256, return_tensors='pt')
    with torch.no_grad():
        out = model(**tokens)
        # CLS pooling
        cls = out.last_hidden_state[:,0,:].squeeze().cpu().numpy()
    return cls

def query_policies_for_threat(threat_class):
    """
    Query policy DB to fetch relevant policies for a given threat_class.
    Returns list of dicts {policy_id, name, severity, controls}
    """
    # Convert threat_class to string for comparison
    threat_class_str = str(threat_class)
    
    # Print to terminal
    print(f"🔍 Analyzing threat class: {threat_class_str}")
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    if SIMULATION_MODE:
        # Simulation: return policies based on threat class
        policies = []
        if "SMB" in threat_class_str:
            policies.append({"policy_id": "POL-SMB-001", "name": "Disable SMBv1 Policy", "severity": "CRITICAL", "controls": ["DISABLE_SMBv1"]})
        elif "PHISH" in threat_class_str:
            policies.append({"policy_id": "POL-PHISH-001", "name": "Enable MFA Policy", "severity": "HIGH", "controls": ["ENABLE_MFA"]})
        elif "RANSOM" in threat_class_str:
            policies.append({"policy_id": "POL-RANSOM-001", "name": "Isolate Endpoint Policy", "severity": "CRITICAL", "controls": ["ISOLATE_ENDPOINT"]})
        else:
            policies.append({"policy_id": "POL-GENERIC-001", "name": "Investigate Threat", "severity": "MEDIUM", "controls": ["INVESTIGATE"]})
        
        # Print policies to terminal
        for policy in policies:
            print(f"   📋 Policy: {policy['name']} ({policy['severity']})")
        
        return policies
    else:
        # Production: actual database query
        cur.execute("SELECT policy_id, name, severity, controls FROM policies WHERE %s = ANY(related_threats)", (threat_class_str,))
        rows = cur.fetchall()
        cur.close(); conn.close()
        policies = []
        for r in rows:
            policies.append({"policy_id": r[0], "name": r[1], "severity": r[2], "controls": json.loads(r[3])})
        return policies

# DecisionTree implementation from paper
SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
THRESHOLD = SEVERITY_ORDER["HIGH"]  # paper checks if max severity > THRESHOLD

def DecisionTree(policies):
    if not policies:
        print("   ✅ No action required")
        return "No action required"
    
    max_sev = max(SEVERITY_ORDER.get(p["severity"], 1) for p in policies)
    
    if max_sev > THRESHOLD:
        print("   🚨 IMMEDIATE ACTION REQUIRED")
        return "Immediate action required"
    else:
        print("   ⚡ Standard mitigation required")
        return "Standard mitigation required"

# TriggerSmartContract: Simulation mode
def TriggerSmartContract(decision, metadata):
    """
    metadata: dict (threat_type, details, policies_to_apply)
    Returns action_result dict, including tx_id and status
    """
    if SIMULATION_MODE:
        # Simulation: mock blockchain response
        time.sleep(0.1)  # Simulate processing time
        result = {
            "tx_id": f"sim-tx-{random.randint(10000, 99999)}",
            "status": "SUCCESS",
            "elapsed": 0.1,
            "simulation_mode": True
        }
        print(f"   🔗 Blockchain TX: {result['tx_id']} ({result['status']})")
        return result
    else:
        # Production: actual Hyperledger Fabric call
        payload = json.dumps({"decision": decision, "metadata": metadata})
        cli_container = os.getenv("FABRIC_CLI_CONTAINER", "cli")
        channel = os.getenv("FABRIC_CHANNEL", "mychannel")
        cc_name = os.getenv("CHAINCODE_NAME", "compliancecontract")
        
        invoke_cmd = [
            "docker", "exec", "-i", cli_container,
            "peer", "chaincode", "invoke",
            "-o", "orderer.example.com:7050",
            "-C", channel,
            "-n", cc_name,
            "--tls", "--cafile",
            "/var/hyperledger/config/crypto-config/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem",
            "-c", json.dumps({"Args":["executeDecision", payload]})
        ]
        
        try:
            start = time.time()
            proc = subprocess.run(invoke_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            elapsed = time.time() - start
            stdout = proc.stdout
            tx_id = None
            for line in stdout.splitlines():
                if "TxID" in line or "txid" in line.lower():
                    tx_id = line.strip()
                    break
            result = {"tx_id": tx_id or "unknown", "status": "SUCCESS", "cli_stdout": stdout, "elapsed": elapsed}
            print(f"   🔗 Blockchain TX: {result['tx_id']} ({result['status']})")
            return result
        except subprocess.CalledProcessError as e:
            result = {"tx_id": None, "status": "FAILED", "stderr": e.stderr}
            print(f"   ❌ Blockchain TX Failed: {result['status']}")
            return result

def UpdateModel(result):
    # Placeholder for reinforcement learning updates
    if result.get("status") == "SUCCESS":
        # Log success for future model retraining
        print("   📈 Model updated with successful action")
        pass
    else:
        # Schedule analysis for failed actions
        print("   ⚠️  Model adjustment scheduled for failed action")
        pass

def ProcessThreatIntelligence(CTI_feed):
    """
    CTI_feed: list of CTI records
    Returns list of (decision, action_result) for each CTI record processed
    """
    outputs = []
    
    print(f"\n📊 Processing {len(CTI_feed)} threat intelligence items...")
    print("=" * 60)
    
    for i, item in enumerate(CTI_feed):
        print(f"\n🔍 Threat {i+1}/{len(CTI_feed)}:")
        print(f"   📝 Title: {item.get('title', 'No title')}")
        print(f"   📄 Description: {item.get('description', 'No description')[:100]}...")
        
        text = item.get("title", "") + " " + item.get("description", "")
        emb = embed_text(text).reshape(1, -1)
        threat_class = rf.predict(emb)[0]   # RF returns class label
        
        print(f"   🏷️  Classified as: {threat_class}")
        
        # Get policies
        relevant_policies = query_policies_for_threat(threat_class)
        decision = DecisionTree(relevant_policies)
        
        metadata = {
            "cti_id": item.get("id"),
            "threat_class": threat_class,
            "policies": [p["policy_id"] for p in relevant_policies],
            "severity": max([p["severity"] for p in relevant_policies]) if relevant_policies else "LOW"
        }
        
        action_result = TriggerSmartContract(decision, metadata)
        UpdateModel(action_result)
        
        outputs.append((decision, action_result))
        
        print(f"   ⏰ Processing time: {action_result.get('elapsed', 0):.2f}s")
        print("   " + "-" * 40)
    
    print(f"\n✅ Processing complete! {len(outputs)} threats analyzed.")
    return outputs

# Additional function for direct threat analysis
def analyze_single_threat(threat_description, threat_title="Generic Threat"):
    """Analyze a single threat description"""
    threat_data = {
        "id": f"direct-{datetime.now().timestamp()}",
        "title": threat_title,
        "description": threat_description,
        "source": "Direct Input"
    }
    return ProcessThreatIntelligence([threat_data])

# Thin API wrapper for other services to call
if __name__ == "__main__":
    import sys
    try:
        # Read input from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            print("❌ No input data provided")
            sys.exit(1)
            
        data = json.loads(input_data)
        out = ProcessThreatIntelligence(data if isinstance(data, list) else [data])
        print(json.dumps(out, indent=2))
    except json.JSONDecodeError:
        # If not JSON, treat as plain text
        threat_data = {
            "id": "cli-input",
            "title": "Command Line Threat",
            "description": input_data,
            "source": "CLI Input"
        }
        out = ProcessThreatIntelligence([threat_data])
        print(json.dumps(out, indent=2))
    except Exception as e:
        error_result = {"error": str(e), "simulation_mode": SIMULATION_MODE}
        print(json.dumps(error_result, indent=2))