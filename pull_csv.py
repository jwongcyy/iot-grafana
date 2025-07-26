import os
import requests
import time
import pandas as pd

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
    
    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code == 200:
        print("Response received from Edenic API")
        data = response.json()
        return data
    else:
        print(f"Failed to fetch telemetry data: HTTP {response.status_code}")
        print(response.text)
        return None

def transform_and_export_csv(data):
    if not data:
        print("No data to process.")
        return
    
    for param_name, param_data in data.items():
        df = pd.DataFrame(param_data)
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df['value'] = df['value'].astype(float)
        
        df = df.rename(columns={
            'ts': '',
            'value': param_name
            })
        
        filename = f"edenic_{param_name}.csv"
        df.to_csv(filename, index=False)
        print(f"Exported {filename} with {len(df)} records")
        
        print(f"\nSample of {filename}:")
        print(df.head(2), "\n" + "-"*50 + "\n")

if __name__ == "__main__":
    data = fetch_telemetry()
    if data:
        transform_and_export_csv(data)
