import os
import requests
import time
import pandas as pd
from pathlib import Path

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
    return start_ts, end_ts

def fetch_telemetry():
    start_ts, end_ts = get_timestamps_past_7_days()
    
    params = {
        "keys": "temperature,electrical_conductivity,ph",
        "startTs": str(start_ts),
        "endTs": str(end_ts),
        "interval": "10800000",  # 3-hour interval
        "agg": "AVG",
        "orderBy": "ASC"
    }
    
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        print("Response received from Edenic API")
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch telemetry data: {e}")
        return None

def transform_and_export_csv(data):
    if not data:
        print("No data to process.")
        return
    
    # Create output directory if it doesn't exist
    output_dir = Path("telemetry_data")
    output_dir.mkdir(exist_ok=True)
    
    exported_files = []
    
    for param_name, param_data in data.items():
        if not param_data:
            print(f"No data available for {param_name}")
            continue
            
        df = pd.DataFrame(param_data)
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        df = df.rename(columns={
            'ts': 'timestamp',
            'value': param_name
        })
        
        filename = output_dir / f"edenic_{param_name}.csv"
        
        try:
            df.to_csv(filename, index=False)
            print(f"Exported {filename} with {len(df)} records")
            exported_files.append(filename)
            
            print(f"\nSample of {filename}:")
            print(df.head(2))
            print("-" * 50 + "\n")
            
        except Exception as e:
            print(f"Error exporting {filename}: {e}")
    
    return exported_files

if __name__ == "__main__":
    data = fetch_telemetry()
    if data:
        exported_files = transform_and_export_csv(data)
        if exported_files:
            print(f"Successfully exported {len(exported_files)} files:")
            for file in exported_files:
                print(f"  - {file}")
        else:
            print("No files were exported.")
