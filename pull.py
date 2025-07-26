import requests
import time

API_URL = "https://api.edenic.io/api/v1/telemetry/a080ca30-4e3a-11f0-9a42-63543a698b74"
API_KEY = "ed_1kw70wywwsb511fw54mb5iwozhdxgoj2bv0jglw99grc5sv3lhi93k1ae45cz0c4"

headers = {
    "Authorization": API_KEY
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
    
    response = requests.get(API_URL, headers=headers, params=params)
    if response.status_code == 200:
        print("Response received:")
        print(response.text)
    else:
        print(f"Failed to fetch telemetry data: HTTP {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    fetch_telemetry()
