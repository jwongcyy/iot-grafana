import os
import requests
import pandas as pd
from datetime import datetime

# read secrets from environment
API_KEY = os.environ.get('API_KEY')
API_URL = os.environ.get('API_URL')

if not API_KEY or not API_URL:
    raise ValueError("Missing required tokens in environment variables.")

headers = {
    "Authorization": API_KEY
}

def fetch_with_known_working_timestamp():
    """Use the exact timestamp from your working curl response"""
    
    # The exact timestamp from your curl that worked
    known_working_ts = 1762865390358
    
    # Try a small window around this timestamp
    params = {
        "keys": "temperature,electrical_conductivity,ph",
        "startTs": str(known_working_ts - 60000),  # 1 minute before
        "endTs": str(known_working_ts + 60000),    # 1 minute after
    }
    
    print(f"🔧 Using known working timestamp: {known_working_ts}")
    print(f"📅 Corresponding date: {datetime.fromtimestamp(known_working_ts/1000)}")
    print(f"🔍 Parameters: {params}")
    
    response = requests.get(API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response received!")
        print(f"📊 Data structure: {list(data.keys())}")
        
        for param, values in data.items():
            print(f"   {param}: {len(values)} data points")
            
        return data
    else:
        print(f"❌ Failed: HTTP {response.status_code}")
        print(f"Response: {response.text}")
        return None

def export_data(data):
    """Export the data to CSV files"""
    if not data:
        return False
        
    for param_name, param_data in data.items():
        df = pd.DataFrame(param_data)
        df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
        df[param_name] = pd.to_numeric(df['value'], errors='coerce')
        
        # Keep only necessary columns
        df = df[['timestamp', param_name]]
        
        filename = f"edenic_{param_name}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Exported {filename} with {len(df)} records")
        
    return True

if __name__ == "__main__":
    print("🎯 Using Known Working Timestamp")
    print("=" * 50)
    
    data = fetch_with_known_working_timestamp()
    if data:
        success = export_data(data)
        if success:
            print(f"\n🎉 Success! CSV files created.")
        else:
            print(f"\n❌ Export failed.")
    else:
        print(f"\n❌ No data received.")
