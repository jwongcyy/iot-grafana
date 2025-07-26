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
    "Authorization": f"Token {API_KEY}"
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
    """
    Transform the JSON data into a DataFrame and export separate CSV files for
    temperature, pH, and electrical conductivity.
    Assumes data["results"] is a list of telemetry records with keys including
    'timestamp', 'temperature', 'ph', 'electrical_conductivity'.
    """

    if not data or 'results' not in data or not data['results']:
        print("No data to process")
        return

    # Create DataFrame from results
    df = pd.DataFrame(data['results'])

    # Convert timestamp from milliseconds epoch to human-readable or keep timestamp as string
    # Example: convert ms to ISO date string (optional, or keep as-is)
    # df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # Rename columns to match your CSV format, including a blank first column for timestamp
    # Here we'll make the first column empty string to match your provided example
    df.rename(columns={
        'timestamp': '',
        'ph': 'pH',
        'temperature': 'Temperature',
        'electrical_conductivity': 'EC'
    }, inplace=True)

    # Reorder columns to have the unnamed time column first (empty string), then pH, Temperature, EC
    # If any columns missing, ignore to avoid errors
    cols_to_keep = [col for col in ['', 'pH', 'Temperature', 'EC'] if col in df.columns]
    df = df[cols_to_keep]

    # Save the modified full CSV (optional)
    df.to_csv('export_mod.csv', index=False)

    # Prepare dictionary for split-export filenames
    split_files = {
        'pH': 'edenic1_ph.csv',
        'Temperature': 'edenic1_temp.csv',
        'EC': 'edenic1_ec.csv'
    }

    # Export the three CSV files: each has timestamp and one measurement column
    for col, filename in split_files.items():
        if col in df.columns:
            split_df = df[['', col]]
            split_df.to_csv(filename, index=False)
            print(f"Exported {filename}")

if __name__ == "__main__":
    data = fetch_telemetry()
    if data:
        transform_and_export_csv(data)
