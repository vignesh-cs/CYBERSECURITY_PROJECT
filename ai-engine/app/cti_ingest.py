import os, requests

XFORCE_URL = "https://api.xforce.ibmcloud.com/..."
API_KEY = os.getenv("XFORCE_KEY")
API_PASS = os.getenv("XFORCE_PASS")

def fetch_cti(query_params):
    # example IBM X-Force feed call
    r = requests.get(XFORCE_URL, auth=(API_KEY, API_PASS), params=query_params)
    r.raise_for_status()
    return r.json()  # returns CTI feed to pass to decision_engine.ProcessThreatIntelligence
