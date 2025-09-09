import os
import sys
import time
import json
from pathlib import Path
from decision_engine import ProcessThreatIntelligence

def scan_existing_files(folder_path):
    """Scan all existing JSON files in folder"""
    print(f"🔍 Scanning existing files in: {folder_path}")
    
    for file_path in Path(folder_path).glob("*.json"):
        print(f"\n📄 Processing existing file: {file_path.name}")
        process_threat_file(str(file_path))

def process_threat_file(file_path):
    """Process a single threat file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            threats = json.load(f)
        
        if not isinstance(threats, list):
            threats = [threats]
        
        print(f"   📊 Found {len(threats)} threats")
        
        # Process with your decision engine
        results = ProcessThreatIntelligence(threats)
        
        for i, (decision, action_result) in enumerate(results):
            threat_desc = threats[i].get('description', 'No description')
            print(f"   🚨 Threat {i+1}: {threat_desc[:80]}...")
            print(f"   ✅ Action: {decision}")
            print(f"   📋 Status: {action_result.get('status')}")
            print(f"   ⏱️  Time: {action_result.get('elapsed', 0):.2f}s")
            print("   " + "-" * 40)
        
        print(f"   ✅ Processed: {len(results)} threats")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    # Folder to watch for threat files
    SCAN_FOLDER = os.path.join(os.path.expanduser("~"), "ThreatScan")
    
    if not os.path.exists(SCAN_FOLDER):
        os.makedirs(SCAN_FOLDER)
        print(f"📁 Created scan folder: {SCAN_FOLDER}")
    
    print("🛡️  AI Threat Auto-Scanner Started!")
    print(f"📁 Monitoring: {SCAN_FOLDER}")
    print("💡 Place JSON files with threat data in this folder")
    print("=" * 60)
    
    # Scan existing files first
    scan_existing_files(SCAN_FOLDER)
    
    print("\n👀 Waiting for new files... (Ctrl+C to stop)")
    print("=" * 60)
    
    # Simple polling method (alternative to watchdog)
    known_files = set()
    
    try:
        while True:
            current_files = set()
            for file_path in Path(SCAN_FOLDER).glob("*.json"):
                current_files.add(str(file_path))
                
                # Check if new file
                if str(file_path) not in known_files:
                    print(f"\n🔍 New file detected: {file_path.name}")
                    process_threat_file(str(file_path))
                    known_files.add(str(file_path))
            
            time.sleep(2)  # Check every 2 seconds
            
    except KeyboardInterrupt:
        print("\n🛑 Scanner stopped by user")