import csv
from datetime import datetime, timedelta

# Constants
START_DATE = "2025-07-01"
END_DATE = "2028-06-30"
BASE_RATE = 0.12  # kg C/day
GROWTH_EXPONENT = 1.6
DAILY_SPIRULINA_L = 100
MUSSEL_COUNT = 7
TEMP_FACTOR = 2  # For 28°C

def calculate_daily_carbon(date):
    days = (date - datetime.strptime(START_DATE, "%Y-%m-%d")).days
    return BASE_RATE * pow(days, GROWTH_EXPONENT) * (0.0005 * DAILY_SPIRULINA_L) * MUSSEL_COUNT * TEMP_FACTOR

# Generate data
with open('musselc.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["", "carbon_kg"])
    
    current_date = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_date = datetime.strptime(END_DATE, "%Y-%m-%d")
    
    while current_date <= end_date:
        daily_carbon = calculate_daily_carbon(current_date)
        writer.writerow([current_date.strftime("%Y-%m-%d"), round(daily_carbon, 3)])
        current_date += timedelta(days=1)