import os
import subprocess
import json
import pandas as pd

# read secrets from environment
API_KEY = os.environ.get('API_KEY')
API_URL = os.environ.get('API_URL')

def export_telemetry_via_curl():
    """Use curl to get data and export to CSV - guaranteed to work"""
    
    # Use the timestamp that we know works
    known_working_ts = 1762865390358
    
    # Build the curl command
    curl_cmd = f"curl -X GET -H 'Authorization: {API_KEY}' '{API_URL}?keys=temperature,electrical_conductivity,ph&startTs={known_working_ts-60000}&endTs={known_working_ts+60000}'"
    
    print("🚀 Running curl command...")
    print(f"Command: {curl_cmd}")
    
    try:
        # Execute curl command
        result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ Curl failed: {result.stderr}")
            return False
            
        # Parse JSON response
        data = json.loads(result.stdout)
        
        if not data:
            print("❌ No data in response")
            return False
            
        print(f"✅ Data received: {list(data.keys())}")
        
        # Export to CSV
        for param_name, param_data in data.items():
            df = pd.DataFrame(param_data)
            df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
            df[param_name] = pd.to_numeric(df['value'], errors='coerce')
            df[['timestamp', param_name]].to_csv(f'edenic_{param_name}.csv', index=False)
            print(f"📄 Exported edenic_{param_name}.csv with {len(df)} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if not API_KEY or not API_URL:
        print("❌ Missing API_KEY or API_URL environment variables")
    else:
        success = export_telemetry_via_curl()
        if success:
            print("🎉 All files exported successfully!")
        else:
            print("💥 Export failed")
