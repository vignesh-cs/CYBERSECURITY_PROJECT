import time, json, random
import sys
import os

# Get the absolute path to the app directory
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)  # This goes up from simulation to app

# Add the app directory to Python path
sys.path.insert(0, app_dir)

from decision_engine import ProcessThreatIntelligence
import numpy as np
from scipy import stats

NUM_ENDPOINTS = 60

# create sample CTI that maps to a policy (e.g., disabling SMBv1)
sample_cti = {
    "id":"cti-smbenable",
    "source":"simulation",
    "timestamp": "2024-12-01T00:00:00Z",
    "title":"SMBv1 detected",
    "description":"Detected SMBv1 enabled on multiple endpoints; exploit possible"
}

# simulate endpoints with states (for more realism you can read from a JSON dataset)
endpoints = [{"id":f"endpoint-{i+1}", "state": {"smbv1":True}} for i in range(NUM_ENDPOINTS)]

auto_times=[]
auto_successes=0
for ep in endpoints:
    start = time.time()
    # create CTI payload per endpoint or global; paper uses global policy application
    decision_results = ProcessThreatIntelligence([sample_cti])
    elapsed = time.time() - start
    auto_times.append(elapsed)
    # inspect action_result for success
    action_result = decision_results[0][1]
    if action_result.get("status") == "SUCCESS":
        auto_successes += 1

CER_auto = (auto_successes / NUM_ENDPOINTS) * 100
ACT_auto = sum(auto_times) / len(auto_times)

# Simulate human-centric times and successes (paper used measured times)
human_times = np.random.normal(loc=2000, scale=300, size=NUM_ENDPOINTS)  # seconds
human_successes = sum(np.random.choice([0,1], size=NUM_ENDPOINTS, p=[0.15,0.85])) # 85% success

CER_human = (human_successes/NUM_ENDPOINTS)*100
ACT_human = human_times.mean()

# Paired t-test on times between automated and human
t_stat, p_val = stats.ttest_rel(human_times, np.array(auto_times))

print(json.dumps({
    "CER_auto": CER_auto,
    "ACT_auto_seconds": ACT_auto,
    "CER_human": CER_human,
    "ACT_human_seconds": ACT_human,
    "t_stat": float(t_stat), 
    "p_val": float(p_val),
    "significance": "AUTOMATION_FASTER" if p_val < 0.05 and t_stat > 0 else "NO_SIGNIFICANT_DIFFERENCE"
}, indent=2))