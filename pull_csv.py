def transform_and_export_csv(data):
    if not data:
        print("No data to process.")
        return
    
    exported_files = []
    
    for param_name, param_data in data.items():
        if not param_data:
            print(f"No data available for {param_name}")
            continue
            
        df = pd.DataFrame(param_data)
        if df.empty:
            print(f"No data in DataFrame for {param_name}")
            continue
            
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        
        df = df.rename(columns={
            'ts': 'timestamp',
            'value': param_name
        })
        
        # Create CSV in current directory (not subdirectory)
        filename = f"edenic_{param_name}.csv"
        
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
