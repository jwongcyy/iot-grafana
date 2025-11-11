import os
import requests
import time
import pandas as pd
import json
from datetime import datetime

# read secrets from environment
API_KEY = os.environ.get('API_KEY')
API_URL = os.environ.get('API_URL')

if not API_KEY or not API_URL:
    raise ValueError("Missing required tokens in environment variables.")

headers = {
    "Authorization": API_KEY
}

def get_timestamps_past_7_days():
    # Current time (end timestamp) in milliseconds
    end_ts = int(time.time() * 1000)
    # Start timestamp = 7 days ago in milliseconds
    start_ts = end_ts - (7 * 24 * 60 * 60 * 1000)
    
    # Debug output to see the actual timestamps
    print(f"Generated timestamps:")
    print(f"  Start TS: {start_ts} ({datetime.fromtimestamp(start_ts/1000).strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"  End TS:   {end_ts} ({datetime.fromtimestamp(end_ts/1000).strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"  Query range: 7 days from {datetime.fromtimestamp(start_ts/1000).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(end_ts/1000).strftime('%Y-%m-%d')}")
    
    return start_ts, end_ts

def fetch_telemetry():
    start_ts, end_ts = get_timestamps_past_7_days()
    
    params = {
        "keys": "ph,temperature,electrical_conductivity",
        "startTs": str(start_ts),
        "endTs": str(end_ts),
        "interval": "10800000",  # 3-hour interval
        "agg": "AVG",
        "orderBy": "ASC"
    }
    
    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code == 200:
        print("Response received from Edenic API")
        data = response.json()
        print(f"API Response keys: {list(data.keys())}")
        return data
    else:
        print(f"Failed to fetch telemetry data: HTTP {response.status_code}")
        print(response.text)
        return None

def transform_and_export_csv(data):
    """
    Transform the JSON data into separate CSV files for each parameter.
    Based on the original code structure where data is organized by parameter names.
    """
    
    if not data:
        print("No data to process")
        return

    print(f"Available parameters in response: {list(data.keys())}")
    
    exported_files = []
    
    for param_name, param_data in data.items():
        print(f"Processing {param_name}: {len(param_data) if param_data else 0} data points")
        
        if not param_data:
            print(f"No data available for {param_name}")
            continue
            
        # Create DataFrame for this parameter
        df = pd.DataFrame(param_data)
        print(f"DataFrame columns for {param_name}: {df.columns.tolist()}")
        
        if df.empty:
            print(f"Empty DataFrame for {param_name}")
            continue
            
        # Convert timestamp and value
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'ts': '',
            'value': param_name
        })
        
        # Create filename based on parameter
        filename = f"edenic_{param_name}.csv"
        
        try:
            # Export to CSV
            df.to_csv(filename, index=False)
            print(f"✅ Exported {filename} with {len(df)} records")
            exported_files.append(filename)
            
            # Show sample
            print(f"Sample of {filename}:")
            print(df.head(2))
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Error exporting {filename}: {e}")
    
    if exported_files:
        print(f"✅ Successfully exported {len(exported_files)} files")
    else:
        print("❌ No files were exported - check data structure")

def debug_api_response(data):
    """Debug function to understand the API response structure"""
    print("\n" + "="*60)
    print("DEBUG API RESPONSE STRUCTURE")
    print("="*60)
    print(f"Top-level keys: {list(data.keys())}")
    
    for key, value in data.items():
        print(f"\nParameter: {key}")
        print(f"Type: {type(value)}")
        if isinstance(value, list):
            print(f"Number of items: {len(value)}")
            if value:
                print(f"First item: {value[0]}")
                print(f"Keys in first item: {list(value[0].keys()) if isinstance(value[0], dict) else 'N/A'}")
        else:
            print(f"Value: {value}")
    print("="*60 + "\n")

if __name__ == "__main__":
    data = fetch_telemetry()
    if data:
        # First, debug the response structure
        debug_api_response(data)
        
        # Then try to export
        transform_and_export_csv(data)
    else:
        print("❌ No data received from API")
