import os
import requests
import time

# read secrets from environment
API_KEY = os.environ.get('API_KEY')
API_URL = os.environ.get('API_URL')

if not API_KEY or not API_URL:
    raise ValueError("Missing required tokens in environment variables.")

headers = {
    "Authorization": f"Token {API_KEY}"
}

def get_timestamps_past_7_days():
    # Current time (end timestamp) in milliseconds
    end_ts = int(time.time() * 1000)
    # Start timestamp = 7 days ago in milliseconds
    start_ts = end_ts - (7 * 24 * 60 * 60 * 1000)
    return start_ts, end_ts     # since Unix epoch 0:00:00 UTC Jan 1, 1970

def fetch_telemetry():
    start_ts, end_ts = get_timestamps_past_7_days()
    
    params = {
        "keys": "temperature,electrical_conductivity,ph",
        "startTs": str(start_ts),
        "endTs": str(end_ts),
        "interval": "10800000",  # 3-hour interval (unchanged)
        "agg": "AVG",
        "orderBy": "ASC"
    }
    
    response = requests.get(f"Token {API_URL}", headers=headers, params=params)
    if response.status_code == 200:
        print("Response received:")
        print(response.text)
    else:
        print(f"Failed to fetch telemetry data: HTTP {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    fetch_telemetry()
