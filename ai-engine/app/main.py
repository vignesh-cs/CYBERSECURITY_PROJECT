import asyncio
import logging
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
import aiohttp
import json
from datetime import datetime
import os
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import tempfile
import threading
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(title="AI Cybersecurity Compliance System", version="2.0.0")

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create directories if they don't exist
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files and templates with correct paths
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Import your decision engine
try:
    from decision_engine import ProcessThreatIntelligence, analyze_single_threat
    DECISION_ENGINE_AVAILABLE = True
    print("✅ Decision engine loaded successfully")
except ImportError as e:
    print(f"⚠️ Decision engine not available: {e}")
    DECISION_ENGINE_AVAILABLE = False
    # Create fallback functions
    def ProcessThreatIntelligence(CTI_feed):
        return [("No action required", {"status": "ERROR", "error": "Decision engine not available"})]
    
    def analyze_single_threat(threat_description):
        return [("No action required", {"status": "ERROR", "error": "Decision engine not available"})]

# Pydantic models
class ThreatAnalysisRequest(BaseModel):
    description: str

class ThreatAnalysisResponse(BaseModel):
    policyId: str
    threatDescription: str
    action: str
    confidence: float
    severity: str
    timestamp: str
    model_version: str

# Global storage for results
compliance_actions = []
threat_intelligence = []

# File watcher configuration
SCAN_FOLDER = os.path.join(os.path.expanduser("~"), "ThreatScan")
os.makedirs(SCAN_FOLDER, exist_ok=True)

def process_threat_file(file_path):
    """Process a single threat file and show output in terminal"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            threats = json.load(f)
        
        if not isinstance(threats, list):
            threats = [threats]
        
        print(f"\n🔍 New threat file detected: {os.path.basename(file_path)}")
        print(f"📊 Found {len(threats)} threats in file")
        print("=" * 60)
        
        # Process with your decision engine
        results = ProcessThreatIntelligence(threats)
        
        for i, (decision, action_result) in enumerate(results):
            threat_desc = threats[i].get('description', 'No description')
            print(f"🚨 Threat {i+1}: {threat_desc[:80]}...")
            print(f"✅ Decision: {decision}")
            print(f"📋 Status: {action_result.get('status', 'UNKNOWN')}")
            print(f"🔗 TX ID: {action_result.get('tx_id', 'N/A')}")
            print(f"⏱️  Time: {action_result.get('elapsed', 0):.2f}s")
            print("-" * 40)
        
        print(f"✅ File processing complete: {len(results)} actions taken")
        print("=" * 60)
        
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON format in {os.path.basename(file_path)}")
    except Exception as e:
        print(f"❌ Error processing file: {e}")

def scan_existing_files():
    """Scan all existing JSON files in folder"""
    print(f"🔍 Scanning existing files in: {SCAN_FOLDER}")
    
    for file_path in Path(SCAN_FOLDER).glob("*.json"):
        process_threat_file(str(file_path))

def start_file_watcher():
    """Start watching for threat files in background"""
    def watch_files():
        known_files = set()
        
        # Scan existing files first
        scan_existing_files()
        
        print(f"\n👀 Watching folder for new threat files: {SCAN_FOLDER}")
        print("💡 Drop JSON files with threat data here for automatic analysis")
        print("=" * 60)
        
        while True:
            try:
                current_files = set()
                for file_path in Path(SCAN_FOLDER).glob("*.json"):
                    current_files.add(str(file_path))
                    
                    # Check if new file
                    if str(file_path) not in known_files:
                        process_threat_file(str(file_path))
                        known_files.add(str(file_path))
                
                time.sleep(3)  # Check every 3 seconds
                
            except Exception as e:
                print(f"File watcher error: {e}")
                time.sleep(5)
    
    # Start file watcher in background thread
    watcher_thread = threading.Thread(target=watch_files, daemon=True)
    watcher_thread.start()
    print("✅ Background file watcher started")

class AIThreatAnalyzer:
    def __init__(self):
        self.model = None
        self.session = None
        self.model_info = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize AI model"""
        try:
            logger.info("Initializing AI Threat Analyzer...")
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            logger.info("HTTP session initialized")
            
            # Load or train model
            await self.load_or_train_model()
            
            self.is_initialized = True
            logger.info("AI Threat Analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    async def load_or_train_model(self):
        """Load pre-trained model or train a new one"""
        model_path = os.path.join(BASE_DIR, 'models', 'threat_classifier_model.pkl')
        model_info_path = os.path.join(BASE_DIR, 'models', 'model_info.pkl')
        
        try:
            # Check if model files exist
            if os.path.exists(model_path) and os.path.exists(model_info_path):
                logger.info("Loading pre-trained model...")
                self.model = joblib.load(model_path)
                self.model_info = joblib.load(model_info_path)
                logger.info(f"Model loaded: {self.model_info['model_type']} v{self.model_info['version']}")
                logger.info(f"Model accuracy: {self.model_info['accuracy']:.3f}")
                logger.info(f"Trained on: {self.model_info['training_date']}")
                
            else:
                logger.warning("No pre-trained model found. Training new model...")
                await self.train_model()
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.info("Training new model as fallback...")
            await self.train_model()

    async def train_model(self):
        """Train the threat classification model"""
        try:
            logger.info("Starting model training...")
            
            # Use default training data
            training_data = self.get_default_training_data()
            
            # Create DataFrame
            df = pd.DataFrame(training_data, columns=['threat_description', 'required_action', 'severity'])
            logger.info(f"Training with {len(df)} samples")
            
            X = df['threat_description']
            y = df['required_action']
            
            # Create and train pipeline
            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=500,
                    stop_words='english',
                    ngram_range=(1, 2),
                    min_df=1,
                    max_df=0.9
                )),
                ('clf', RandomForestClassifier(
                    n_estimators=50,
                    random_state=42,
                    class_weight='balanced',
                    max_depth=5
                ))
            ])
            
            pipeline.fit(X, y)
            self.model = pipeline
            
            train_accuracy = pipeline.score(X, y)
            logger.info(f"Model training completed. Training accuracy: {train_accuracy:.3f}")
            
            os.makedirs(os.path.join(BASE_DIR, 'models'), exist_ok=True)
            joblib.dump(pipeline, os.path.join(BASE_DIR, 'models', 'threat_classifier_model.pkl'))
            
            self.model_info = {
                'model_type': 'RandomForestClassifier',
                'version': '1.0.0',
                'training_date': datetime.utcnow().isoformat(),
                'accuracy': float(train_accuracy),
                'training_samples': len(X),
                'test_samples': 0,
                'classes': list(df['required_action'].unique()),
                'features': 500
            }
            
            joblib.dump(self.model_info, os.path.join(BASE_DIR, 'models', 'model_info.pkl'))
            logger.info("Model saved successfully")
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            raise

    def get_default_training_data(self):
        """Return default training data"""
        return [
            ("ransomware encryption files using SMBv1 vulnerability", "DISABLE_SMBv1", "CRITICAL"),
            ("phishing email attempting credential theft", "ENABLE_MFA", "HIGH"),
            ("exploit targeting remote desktop protocol port 3389", "BLOCK_RDP_PORT", "CRITICAL"),
            ("unauthorized access attempt from external IP", "QUARANTINE_ENDPOINT", "HIGH"),
            ("data exfiltration over network shares", "ENABLE_DLP", "HIGH"),
            ("ddos attack targeting network infrastructure", "RATE_LIMIT_TRAFFIC", "HIGH"),
            ("malware execution detected on endpoint", "ISOLATE_ENDPOINT", "CRITICAL"),
            ("sql injection attempt on web application", "WAF_UPDATE", "MEDIUM"),
            ("brute force attack on user accounts", "LOCK_ACCOUNTS", "HIGH"),
            ("suspicious PowerShell execution", "RESTRICT_PS", "MEDIUM"),
            ("weak password policy detected", "PASSWORD_POLICY", "MEDIUM"),
            ("unencrypted data transmission", "ENABLE_ENCRYPTION", "HIGH"),
            ("missing security patches", "APPLY_PATCHES", "HIGH"),
            ("excessive user privileges", "REVIEW_PERMISSIONS", "MEDIUM"),
            ("open network ports", "CLOSE_PORTS", "MEDIUM"),
            ("disabled antivirus", "ENABLE_ANTIVIRUS", "HIGH"),
            ("disabled firewall", "ENABLE_FIREWALL", "HIGH"),
            ("outdated software version", "UPDATE_SOFTWARE", "MEDIUM"),
            ("suspicious network traffic", "INVESTIGATE_TRAFFIC", "HIGH"),
            ("unauthorized software installation", "REMOVE_SOFTWARE", "MEDIUM")
        ]

    async def analyze_threat(self, threat_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze threat and recommend action"""
        try:
            if not self.model:
                raise ValueError("Model not initialized")
            
            threat_description = threat_data.get('description', '')
            if not threat_description:
                raise ValueError("No threat description provided")
            
            logger.info(f"Analyzing threat: {threat_description[:100]}...")
            
            predicted_action = self.model.predict([threat_description])[0]
            confidence_scores = self.model.predict_proba([threat_description])[0]
            confidence = float(np.max(confidence_scores))
            
            policy = self.get_policy_for_action(predicted_action)
            
            result = {
                'policyId': policy.get('id', 'unknown'),
                'threatDescription': threat_description,
                'action': predicted_action,
                'confidence': confidence,
                'severity': policy.get('severity', 'MEDIUM'),
                'timestamp': datetime.utcnow().isoformat(),
                'model_version': self.model_info.get('version', '1.0.0') if self.model_info else 'unknown'
            }
            
            logger.info(f"Threat analysis complete: {result['action']} (confidence: {result['confidence']:.3f})")
            return result
            
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}")
            raise

    def get_policy_for_action(self, action: str) -> Dict[str, Any]:
        """Get policy details for a specific action"""
        policy_map = {
            "DISABLE_SMBv1": {"id": "POL-001", "severity": "CRITICAL"},
            "ENABLE_MFA": {"id": "POL-002", "severity": "HIGH"},
            "BLOCK_RDP_PORT": {"id": "POL-003", "severity": "CRITICAL"},
            "QUARANTINE_ENDPOINT": {"id": "POL-004", "severity": "HIGH"},
            "ENABLE_DLP": {"id": "POL-005", "severity": "HIGH"},
            "RATE_LIMIT_TRAFFIC": {"id": "POL-006", "severity": "HIGH"},
            "ISOLATE_ENDPOINT": {"id": "POL-007", "severity": "CRITICAL"},
            "WAF_UPDATE": {"id": "POL-008", "severity": "MEDIUM"},
            "LOCK_ACCOUNTS": {"id": "POL-009", "severity": "HIGH"},
            "RESTRICT_PS": {"id": "POL-010", "severity": "MEDIUM"},
            "PASSWORD_POLICY": {"id": "POL-011", "severity": "MEDIUM"},
            "ENABLE_ENCRYPTION": {"id": "POL-012", "severity": "HIGH"},
            "APPLY_PATCHES": {"id": "POL-013", "severity": "HIGH"},
            "REVIEW_PERMISSIONS": {"id": "POL-014", "severity": "MEDIUM"},
            "CLOSE_PORTS": {"id": "POL-015", "severity": "MEDIUM"},
            "ENABLE_ANTIVIRUS": {"id": "POL-016", "severity": "HIGH"},
            "ENABLE_FIREWALL": {"id": "POL-017", "severity": "HIGH"},
            "UPDATE_SOFTWARE": {"id": "POL-018", "severity": "MEDIUM"},
            "INVESTIGATE_TRAFFIC": {"id": "POL-019", "severity": "HIGH"},
            "REMOVE_SOFTWARE": {"id": "POL-020", "severity": "MEDIUM"}
        }
        return policy_map.get(action, {'id': 'unknown', 'severity': 'MEDIUM'})

# Global analyzer instance
analyzer = AIThreatAnalyzer()

@app.on_event("startup")
async def startup_event():
    """Initialize when the app starts"""
    print("=" * 60)
    print("🚀 AI Cybersecurity Compliance System Starting...")
    print("📊 Initializing models...")
    await analyzer.initialize()
    
    # Start background file watcher
    start_file_watcher()
    
    print("✅ Models initialized successfully")
    print("🌐 Web server: http://localhost:8000")
    print("📝 Terminal output: Active")
    print(f"📁 Auto-scan folder: {SCAN_FOLDER}")
    print("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when the app shuts down"""
    if analyzer.session:
        await analyzer.session.close()

# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

# API Routes
@app.post("/api/analyze-threat")
async def analyze_threat(request: ThreatAnalysisRequest):
    """Analyze a threat description"""
    try:
        print(f"\n📊 Processing threat: {request.description[:100]}...")
        
        if DECISION_ENGINE_AVAILABLE:
            # Use your decision engine
            results = analyze_single_threat(request.description)
        else:
            # Use built-in analyzer
            result = await analyzer.analyze_threat({"description": request.description})
            results = [(result['action'], {"status": "SUCCESS", "confidence": result['confidence']})]
        
        # Store for frontend
        for decision, action_result in results:
            action_data = {
                "id": f"action-{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "action_taken": decision,
                "policy_id": "AUTO-GENERATED",
                "severity": "HIGH" if "IMMEDIATE" in str(decision) else "MEDIUM",
                "status": action_result.get("status", "UNKNOWN"),
                "confidence": action_result.get("confidence", 0.95),
                "threat_description": request.description
            }
            compliance_actions.append(action_data)
        
        print(f"✅ Analysis complete: {results[0][0]}")
        return {"results": results, "actions": compliance_actions[-len(results):]}
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/analyze-file")
async def analyze_threat_file(file: UploadFile = File(...), file_type: str = Form("auto")):
    """Analyze threats from a file"""
    try:
        print(f"\n📁 Processing file: {file.filename}")
        
        content = await file.read()
        threats = []
        
        if file_type == "json" or file.filename.endswith('.json'):
            data = json.loads(content)
            threats = data if isinstance(data, list) else [data]
        elif file_type == "log" or file.filename.endswith('.log'):
            lines = content.decode().split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    threats.append({
                        "id": f"log-line-{i}",
                        "title": "Log Threat",
                        "description": line.strip(),
                        "source": "Log File"
                    })
        else:
            threats = [{
                "id": "text-input",
                "title": "Text Input",
                "description": content.decode(),
                "source": "Text File"
            }]
        
        print(f"📊 Found {len(threats)} threats in file")
        
        if DECISION_ENGINE_AVAILABLE:
            results = ProcessThreatIntelligence(threats)
        else:
            results = []
            for threat in threats:
                result = await analyzer.analyze_threat(threat)
                results.append((result['action'], {"status": "SUCCESS", "confidence": result['confidence']}))
        
        # Store results
        for i, (decision, action_result) in enumerate(results):
            action_data = {
                "id": f"file-action-{datetime.now().timestamp()}-{i}",
                "timestamp": datetime.now().isoformat(),
                "action_taken": decision,
                "policy_id": "FILE-BASED",
                "severity": "HIGH" if "IMMEDIATE" in str(decision) else "MEDIUM",
                "status": action_result.get("status", "UNKNOWN"),
                "confidence": action_result.get("confidence", 0.92),
                "threat_description": threats[i].get("description", "Unknown threat")
            }
            compliance_actions.append(action_data)
        
        print(f"✅ File processing complete: {len(results)} actions taken")
        return {
            "filename": file.filename,
            "processed_threats": len(threats),
            "actions_taken": len(results)
        }
        
    except Exception as e:
        print(f"❌ File processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")

# Frontend Data APIs
@app.get("/api/compliance/actions")
async def get_compliance_actions():
    """Get compliance actions for frontend"""
    return compliance_actions[-50:]

@app.get("/api/policies")
async def get_policies():
    """Get policies for frontend"""
    return [
        {
            "id": "POL-SMB-001",
            "standard": "NIST",
            "control": "AC-3",
            "description": "Disable SMBv1 protocol",
            "severity": "CRITICAL",
            "required_action": "DISABLE_SMBv1"
        },
        {
            "id": "POL-PHISH-001", 
            "standard": "ISO27001",
            "control": "A.9.2.1",
            "description": "Enable Multi-Factor Authentication",
            "severity": "HIGH",
            "required_action": "ENABLE_MFA"
        }
    ]

@app.get("/api/threats")
async def get_threats():
    """Get threat intelligence for frontend"""
    return threat_intelligence[-20:]

@app.get("/api/health/stats")
async def get_health_stats():
    """Get health stats for dashboard"""
    return {
        "complianceRate": 98,
        "activeThreats": len([a for a in compliance_actions if a.get("status") == "SUCCESS"]),
        "actionsToday": len(compliance_actions)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "actions_processed": len(compliance_actions),
        "decision_engine_available": DECISION_ENGINE_AVAILABLE
    }

@app.get("/model-info")
async def model_info():
    """Get information about the trained model"""
    if not analyzer.model_info:
        raise HTTPException(status_code=404, detail="Model not trained yet")
    return analyzer.model_info

if __name__ == '__main__':
    import uvicorn
    print("Starting AI Cybersecurity Compliance System...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")