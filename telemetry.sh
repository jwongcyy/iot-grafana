#!/bin/bash

# Read secrets from .secrets file
echo "🔍 Loading secrets from .secrets file..."
if [ -f .secrets ]; then
    source .secrets
    echo "✅ Secrets loaded successfully"
else
    echo "❌ .secrets file not found"
    exit 1
fi

# Validate required variables
if [ -z "$API_KEY" ] || [ -z "$API_URL" ]; then
    echo "❌ Missing required environment variables in .secrets file"
    exit 1
fi

echo "🔧 API URL: $API_URL"
echo "🔑 API Key present: ${#API_KEY} characters"

# Set variables for the script
API_KEY="$API_KEY"
API_URL="$API_URL"
TIMESTAMP=$(date +%s000)
START_TS=$((TIMESTAMP - 7*24*60*60*1000))

echo "🚀 Starting Edenic Telemetry Export"
echo "=================================================="

# Fetch data via curl
echo "🔧 Fetching telemetry data..."
response=$(curl -s -X GET \
  -H "Authorization: $API_KEY" \
  "$API_URL?keys=temperature,electrical_conductivity,ph&startTs=$START_TS&endTs=$TIMESTAMP&interval=10800000&agg=AVG&orderBy=ASC")

# Check if response is valid
if [ -z "$response" ]; then
    echo "❌ Empty response from API"
    exit 1
fi

# Check if response is valid JSON
if ! echo "$response" | jq empty 2>/dev/null; then
    echo "❌ Invalid JSON response"
    echo "Response: $response"
    exit 1
fi

echo "✅ Data received successfully"

# Create CSV files using jq
echo "📊 Creating CSV files..."

# Temperature CSV
echo "timestamp,temperature" > edenic_temperature.csv
echo "$response" | jq -r '.temperature[]? | [.ts, .value] | @csv' >> edenic_temperature.csv
temp_count=$(( $(wc -l < edenic_temperature.csv) - 1 ))
echo "✅ Created edenic_temperature.csv with $temp_count records"

# pH CSV
echo "timestamp,ph" > edenic_ph.csv
echo "$response" | jq -r '.ph[]? | [.ts, .value] | @csv' >> edenic_ph.csv
ph_count=$(( $(wc -l < edenic_ph.csv) - 1 ))
echo "✅ Created edenic_ph.csv with $ph_count records"

# Electrical Conductivity CSV
echo "timestamp,electrical_conductivity" > edenic_electrical_conductivity.csv
echo "$response" | jq -r '.electrical_conductivity[]? | [.ts, .value] | @csv' >> edenic_electrical_conductivity.csv
ec_count=$(( $(wc -l < edenic_electrical_conductivity.csv) - 1 ))
echo "✅ Created edenic_electrical_conductivity.csv with $ec_count records"

echo "=================================================="
echo "🎉 Export completed successfully!"
