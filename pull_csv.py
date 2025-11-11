import os
import requests
import time
import pandas as pd
import json
from datetime import datetime, timedelta

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

def debug_api_call():
    """Make test API calls to understand the issue"""
    start_ts, end_ts = get_timestamps_past_7_days()
    
    # Convert to readable dates for debugging
    start_dt = datetime.fromtimestamp(start_ts/1000)
    end_dt = datetime.fromtimestamp(end_ts/1000)
    print(f"Time range: {start_dt} to {end_dt}")
    
    # Test different parameter combinations
    test_cases = [
        {
            "name": "Original parameters",
            "params": {
                "keys": "temperature,electrical_conductivity,ph",
                "startTs": str(start_ts),
                "endTs": str(end_ts),
                "interval": "10800000",  # 3-hour interval
                "agg": "AVG",
                "orderBy": "ASC"
            }
        },
        {
            "name": "Single parameter - temperature",
            "params": {
                "keys": "temperature",
                "startTs": str(start_ts),
                "endTs": str(end_ts),
                "interval": "10800000",
                "agg": "AVG",
                "orderBy": "ASC"
            }
        },
        {
            "name": "No aggregation",
            "params": {
                "keys": "temperature",
                "startTs": str(start_ts),
                "endTs": str(end_ts),
                "orderBy": "ASC"
            }
        },
        {
            "name": "Different time range (last 24 hours)",
            "params": {
                "keys": "temperature",
                "startTs": str(end_ts - (24 * 60 * 60 * 1000)),  # 24 hours ago
                "endTs": str(end_ts),
                "interval": "3600000",  # 1-hour interval
                "agg": "AVG",
                "orderBy": "ASC"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i+1}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            response = requests.get(API_URL, headers=headers, params=test_case['params'], timeout=30)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                print(f"Response length: {len(str(data))} characters")
                
                if data:
                    print("Sample of response content:")
                    print(json.dumps(data, indent=2)[:500] + "..." if len(str(data)) > 500 else json.dumps(data, indent=2))
                else:
                    print("Response is empty")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")

def fetch_telemetry_with_fallback():
    """Try multiple approaches to get data"""
    start_ts, end_ts = get_timestamps_past_7_days()
    
    # Try different parameter combinations
    attempts = [
        # Original attempt
        {
            "keys": "temperature,electrical_conductivity,ph",
            "startTs": str(start_ts),
            "endTs": str(end_ts),
            "interval": "10800000",
            "agg": "AVG",
            "orderBy": "ASC"
        },
        # Try without interval
        {
            "keys": "temperature",
            "startTs": str(start_ts),
            "endTs": str(end_ts),
            "agg": "AVG",
            "orderBy": "ASC"
        },
        # Try raw data without aggregation
        {
            "keys": "temperature",
            "startTs": str(start_ts),
            "endTs": str(end_ts),
            "orderBy": "ASC"
        }
    ]
    
    for i, params in enumerate(attempts):
        print(f"\nAttempt {i+1} with params: {params}")
        response = requests.get(API_URL, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                print(f"✅ Success with attempt {i+1}")
                return data
            else:
                print(f"❌ Attempt {i+1}: Empty response")
        else:
            print(f"❌ Attempt {i+1}: HTTP {response.status_code}")
    
    return None

if __name__ == "__main__":
    print("Starting API debugging...")
    
    # First, run debug to understand the API behavior
    debug_api_call()
    
    # Then try to fetch data with fallback approaches
    print(f"\n{'#'*60}")
    print("ATTEMPTING TO FETCH DATA WITH FALLBACKS")
    print(f"{'#'*60}")
    
    data = fetch_telemetry_with_fallback()
    
    if data:
        print(f"✅ Successfully fetched data with keys: {list(data.keys())}")
        # Here you would call your transform function
    else:
        print("❌ All attempts failed to fetch data")
        print("\nPossible issues:")
        print("1. No data exists for the specified time range")
        print("2. The parameter names are incorrect")
        print("3. The API endpoint requires different parameters")
        print("4. The device might not be sending data")
        print("5. Check if you need to specify a device ID or other identifier")
