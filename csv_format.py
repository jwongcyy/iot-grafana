import pandas as pd

# Read the CSV file (note the first empty column will be automatically handled)
df = pd.read_csv('export.csv')

# Rename the columns
df.columns = ['date', 'pH', 'Temperature', 'EC']

# Save the modified full CSV
df.to_csv('export_mod.csv', index=False)

# Create and save the three split files
split_files = {
    'pH': 'edenic1_ph.csv',
    'Temperature': 'edenic1_temp.csv',
    'EC': 'edenic1_ec.csv'
}

for col, filename in split_files.items():
    split_df = df[['date', col]]
    split_df.to_csv(filename, index=False)