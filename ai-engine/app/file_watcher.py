import time
import json
import os
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from decision_engine import ProcessThreatIntelligence

class ThreatFileHandler(FileSystemEventHandler):
    def __init__(self, watch_folder):
        self.watch_folder = watch_folder
        self.processed_files = set()
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.process_file(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.process_file(event.src_path)
    
    def process_file(self, file_path):
        # Avoid processing the same file multiple times
        if file_path in self.processed_files:
            return
            
        self.processed_files.add(file_path)
        print(f"🔍 New threat file detected: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                threats = json.load(f)
            
            if not isinstance(threats, list):
                threats = [threats]
            
            print(f"📊 Found {len(threats)} threats in file")
            print("=" * 60)
            
            # Process threats using your decision engine
            results = ProcessThreatIntelligence(threats)
            
            print("\n🚨 THREAT ANALYSIS RESULTS:")
            print("=" * 60)
            
            for i, (decision, action_result) in enumerate(results):
                print(f"\nThreat {i+1}:")
                print(f"   Description: {threats[i].get('description', 'No description')[:100]}...")
                print(f"   Decision: {decision}")
                print(f"   Status: {action_result.get('status', 'UNKNOWN')}")
                print(f"   TX ID: {action_result.get('tx_id', 'N/A')}")
                print(f"   Time: {action_result.get('elapsed', 0):.2f}s")
                print("-" * 40)
            
            print(f"\n✅ File processing complete: {len(results)} actions taken")
            
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON format in {file_path}")
        except Exception as e:
            print(f"❌ Error processing file: {e}")

def start_file_watcher(watch_folder):
    """Start watching for threat JSON files"""
    if not os.path.exists(watch_folder):
        os.makedirs(watch_folder)
        print(f"📁 Created watch folder: {watch_folder}")
    
    print(f"👀 Watching folder for threat files: {watch_folder}")
    print("💡 Drop JSON files with threat data here for automatic analysis")
    print("=" * 60)
    
    event_handler = ThreatFileHandler(watch_folder)
    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    # Default watch folder (change as needed)
    WATCH_FOLDER = os.path.join(os.path.expanduser("~"), "ThreatScan")
    start_file_watcher(WATCH_FOLDER)