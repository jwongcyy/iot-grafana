import requests
import os
from datetime import datetime

API_KEY = os.environ.get("API_KEY")
API_URL = os.environ.get("API_URL") # This should be the full URL including device ID

# 1. First, let's see the current real time
current_real_ts = int(datetime.now().timestamp() * 1000)
print(f"Current real-world timestamp (from datetime): {current_real_ts}")
print(f"That date is: {datetime.fromtimestamp(current_real_ts/1000)}")
print("-" * 50)

# 2. Make a simple request for the latest data point
headers = {"Authorization": f"Bearer {API_KEY}"}
params = {"keys": "temperature"}  # Just ask for one sensor

try:
    resp = requests.get(API_URL, headers=headers, params=params, timeout=15)
    print(f"API Response Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"API Response Body: {data}")
        
        # Find the latest timestamp in the response
        if data.get('temperature'):
            latest_point = data['temperature'][-1]  # Get last item
            latest_ts = latest_point['ts']
            latest_val = latest_point['value']
            print(f"\nLatest reading from device:")
            print(f"  Timestamp: {latest_ts}")
            print(f"  Date: {datetime.fromtimestamp(latest_ts/1000)}")
            print(f"  Temperature Value: {latest_val}")
        else:
            print("No 'temperature' data found in response.")
    else:
        print(f"API Error: {resp.text}")
        
except Exception as e:
    print(f"Request failed: {e}")
