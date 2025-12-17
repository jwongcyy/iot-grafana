import requests
import os
from datetime import datetime

API_KEY = os.environ.get("API_KEY")  # Should be in format: ed_12345...
API_URL = os.environ.get("API_URL")  # Full URL with device ID

# 1. First, let's see the current real time
current_real_ts = int(datetime.now().timestamp() * 1000)
print(f"Current real-world timestamp: {current_real_ts}")
print(f"That date is: {datetime.fromtimestamp(current_real_ts/1000)}")
print("-" * 50)

# 2. CRITICAL FIX: Use Edenic-specific header format
# Remove any "Bearer " prefix if present, ensure it starts with "ed_"
api_key_clean = API_KEY.strip()
if api_key_clean.startswith("Bearer "):
    api_key_clean = api_key_clean[7:].strip()  # Remove "Bearer " prefix

print(f"Using API key (first 20 chars): {api_key_clean[:20]}...")
headers = {"Authorization": api_key_clean}  # Just the key itself

# 3. Make a simple request for the latest data point
params = {"keys": "temperature"}

try:
    resp = requests.get(API_URL, headers=headers, params=params, timeout=15)
    print(f"API Response Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"API Response Body: {data}")
        
        if data.get('temperature'):
            latest_point = data['temperature'][-1]
            latest_ts = latest_point['ts']
            latest_val = latest_point['value']
            print(f"\nLatest reading from device:")
            print(f"  Timestamp: {latest_ts}")
            print(f"  Date: {datetime.fromtimestamp(latest_ts/1000)}")
            print(f"  Temperature Value: {latest_val}")
        else:
            print("No 'temperature' data found in response.")
    else:
        print(f"API Error Response: {resp.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
