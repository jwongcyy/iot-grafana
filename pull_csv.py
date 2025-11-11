import os
import requests
import time
import pandas as pd
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

def get_recent_timestamps():
    """Get timestamps for recent data - using a wider range to ensure we get data"""
    # Current time (end timestamp) in milliseconds
    end_ts = int(time.time() * 1000)
    # Start timestamp = 30 days ago in milliseconds to ensure we get data
    start_ts = end_ts - (30 * 24 * 60 * 60 * 1000)
    return start_ts, end_ts

def fetch_telemetry():
    start_ts, end_ts = get_recent_timestamps()
    
    # Convert to readable dates for debugging
    start_dt = datetime.fromtimestamp(start_ts/1000)
    end_dt = datetime.fromtimestamp(end_ts/1000)
    print(f"Fetching data from {start_dt} to {end_dt}")
    
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
        print("✅ Response received from Edenic API")
        data = response.json()
        print(f"📊 Data structure: {list(data.keys())}")
        
        # Print data summary
        for param, values in data.items():
            print(f"   {param}: {len(values)} data points")
            if values:
                # Convert timestamp to readable date
                first_ts = values[0]['ts']
                first_dt = datetime.fromtimestamp(first_ts/1000)
                last_ts = values[-1]['ts'] if len(values) > 1 else first_ts
                last_dt = datetime.fromtimestamp(last_ts/1000)
                print(f"     Time range: {first_dt} to {last_dt}")
                
        return data
    else:
        print(f"❌ Failed to fetch telemetry data: HTTP {response.status_code}")
        print(response.text)
        return None

def transform_and_export_csv(data):
    """
    Transform the JSON data into separate CSV files for each parameter.
    Based on the curl response structure: {"ph":[{"ts":1762865390358,"value":"8.25"}], ...}
    """
    
    if not data:
        print("❌ No data to process")
        return False

    print(f"\n📁 Exporting data for parameters: {list(data.keys())}")
    
    exported_files = []
    
    for param_name, param_data in data.items():
        print(f"\n🔧 Processing {param_name}: {len(param_data)} data points")
        
        if not param_data:
            print(f"   ⚠️ No data available for {param_name}")
            continue
            
        # Create DataFrame for this parameter
        df = pd.DataFrame(param_data)
        
        # Convert timestamp from milliseconds to datetime
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        
        # Convert value to numeric (handles string values like "8.25")
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna()
        
        if df.empty:
            print(f"   ⚠️ No valid data after cleaning for {param_name}")
            continue
            
        # Rename columns for CSV export
        df = df.rename(columns={
            'ts': 'timestamp',
            'value': param_name
        })
        
        # Create filename
        filename = f"edenic_{param_name}.csv"
        
        try:
            # Export to CSV
            df.to_csv(filename, index=False)
            print(f"   ✅ Exported {filename} with {len(df)} records")
            
            # Show sample data
            print(f"   📊 Sample data:")
            print(f"      Timestamp: {df['timestamp'].iloc[0]}")
            print(f"      {param_name}: {df[param_name].iloc[0]}")
            
            exported_files.append(filename)
            
        except Exception as e:
            print(f"   ❌ Error exporting {filename}: {e}")
    
    if exported_files:
        print(f"\n🎉 Successfully exported {len(exported_files)} files:")
        for file in exported_files:
            print(f"   📄 {file}")
        return True
    else:
        print("\n❌ No files were exported")
        return False

def create_combined_csv(data):
    """Create a combined CSV with all parameters in one file"""
    if not data:
        return
        
    # Find the longest data series to use as base
    longest_param = max(data.keys(), key=lambda x: len(data[x]))
    base_df = pd.DataFrame(data[longest_param])
    base_df['timestamp'] = pd.to_datetime(base_df['ts'], unit='ms')
    
    # Create combined DataFrame
    combined_data = []
    
    # Get all unique timestamps
    all_timestamps = set()
    for param_data in data.values():
        for point in param_data:
            all_timestamps.add(point['ts'])
    
    # Sort timestamps
    sorted_timestamps = sorted(all_timestamps)
    
    # Build combined data
    for ts in sorted_timestamps:
        row = {'timestamp': pd.to_datetime(ts, unit='ms')}
        for param_name, param_data in data.items():
            # Find value for this timestamp
            value = None
            for point in param_data:
                if point['ts'] == ts:
                    value = point['value']
                    break
            row[param_name] = value
        combined_data.append(row)
    
    combined_df = pd.DataFrame(combined_data)
    
    # Export combined CSV
    combined_df.to_csv('edenic_combined.csv', index=False)
    print(f"📊 Exported combined CSV with {len(combined_df)} records")
    return combined_df

if __name__ == "__main__":
    print("🚀 Starting Edenic Telemetry Export")
    print("=" * 50)
    
    data = fetch_telemetry()
    if data:
        success = transform_and_export_csv(data)
        
        # Also create a combined CSV
        combined_df = create_combined_csv(data)
        
        if success:
            print(f"\n✅ Script completed successfully!")
        else:
            print(f"\n⚠️ Script completed but no data was exported")
    else:
        print(f"\n❌ Failed to fetch data from API")
