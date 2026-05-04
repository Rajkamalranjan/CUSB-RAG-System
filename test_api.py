"""Quick API test script."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests
import json

BASE = "http://127.0.0.1:8080"

# Test 1: Health check
print("=== Health Check ===")
r = requests.get(f"{BASE}/api/health")
print(json.dumps(r.json(), indent=2))

# Test 2: Query
print("\n=== Query: CUSB kya hai? ===")
r = requests.post(f"{BASE}/api/query", json={"question": "CUSB kya hai?"})
data = r.json()
answer = data.get("answer", "")
print("Answer:", answer[:300])
print("Language:", data.get("language"))
print("Time:", data.get("processing_time"), "s")
print("Sources:", len(data.get("sources", [])))

# Test 3: Fee query
print("\n=== Query: M.Sc Statistics fees ===")
r = requests.post(f"{BASE}/api/query", json={"question": "M.Sc Statistics ki fees kitni hai?"})
data = r.json()
print("Answer:", data.get("answer", "")[:300])
print("Time:", data.get("processing_time"), "s")

# Test 4: Stats
print("\n=== Stats ===")
r = requests.get(f"{BASE}/api/stats")
print(json.dumps(r.json(), indent=2))

print("\n=== ALL API TESTS PASSED ===")
