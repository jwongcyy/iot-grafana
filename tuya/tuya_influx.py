import requests
import json
import time
import hashlib
import hmac
import os
import urllib.parse
from datetime import datetime, timezone
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load environment variables from .env file
load_dotenv()

class TuyaTemperatureLogger:
    def __init__(self):
        # Tuya configuration
        self.client_id = os.getenv('TUYA_ACCESS_ID')
        self.secret = os.getenv('TUYA_ACCESS_SECRET')
        self.device_id = os.getenv('TUYA_DEVICE_ID')
        self.region = os.getenv('REGION', 'tuyaus').lower()
        self.base_url = self._get_base_url_from_region()
        self.access_token = None
        
        # InfluxDB configuration
        self.influx_url = os.getenv('INFLUXDB_URL')
        self.influx_token = os.getenv('INFLUXDB_TOKEN')
        self.influx_org = os.getenv('INFLUXDB_ORG', 'tuya')
        self.influx_bucket = os.getenv('INFLUXDB_BUCKET', 'iot_devices')
        
        # Validate configuration
        if not all([self.client_id, self.secret, self.device_id]):
            raise ValueError("Missing required Tuya configuration in .env file")
        
        if not all([self.influx_url, self.influx_token]):
            print("⚠️ InfluxDB not configured - data will not be exported")
            self.influx_client = None
        else:
            self.influx_client = InfluxDBClient(
                url=self.influx_url,
                token=self.influx_token,
                org=self.influx_org
            )
            print(f"✅ InfluxDB configured for bucket: {self.influx_bucket}")
    
    def _get_base_url_from_region(self):
        region_urls = {
            'tuyacn': 'https://openapi.tuyacn.com',
            'tuyaus': 'https://openapi.tuyaus.com',
            'tuyaeu': 'https://openapi.tuyaeu.com',
            'tuyain': 'https://openapi.tuyain.com'
        }
        return region_urls.get(self.region, 'https://openapi.tuyaus.com')
    
    def get_access_token(self):
        if self.access_token:
            return self.access_token
            
        endpoint = "/v1.0/token"
        timestamp = str(int(time.time() * 1000))
        
        sign_str = f"GET\n{hashlib.sha256(b'').hexdigest()}\n\n{endpoint}?grant_type=1"
        signature = hmac.new(
            self.secret.encode('utf-8'),
            (self.client_id + "" + timestamp + "" + sign_str).encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        headers = {
            'client_id': self.client_id,
            'sign': signature,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
        }
        
        response = requests.get(f"{self.base_url}{endpoint}?grant_type=1", headers=headers)
        result = response.json()
        
        if result['success']:
            self.access_token = result['result']['access_token']
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {result.get('msg')}")
    
    def get_temperature_data(self):
        access_token = self.get_access_token()
        endpoint = f"/v1.0/devices/{self.device_id}/status"
        timestamp = str(int(time.time() * 1000))
        
        sign_str = f"GET\n{hashlib.sha256(b'').hexdigest()}\n\n{endpoint}"
        signature = hmac.new(
            self.secret.encode('utf-8'),
            (self.client_id + access_token + timestamp + "" + sign_str).encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        headers = {
            'client_id': self.client_id,
            'access_token': access_token,
            'sign': signature,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
        }
        
        response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
        result = response.json()
        
        if result['success']:
            for status in result['result']:
                if status['code'] == 'temp_current':
                    return status['value'] / 10.0  # Convert to actual temperature
        
        return None
    
    def log_temperature_to_influxdb(self):
        temperature = self.get_temperature_data()
        
        if temperature is None:
            print("❌ No temperature data found")
            return False
        
        if not self.influx_client:
            print(f"📊 Temperature: {temperature}°C (InfluxDB not configured)")
            return False
        
        # Create data in the specified format
        data = {
            "point1": {
                "tuya_temp": temperature,
            }
        }
        
        for key in data:
            point = (
                Point("tuya_5in1")
                .tag("device_id", self.device_id)
                .field("temperature", data[key]["tuya_temp"])
            )
            
            self.influx_client.write_api(write_options=SYNCHRONOUS).write(
                bucket=self.influx_bucket,
                org=self.influx_org,
                record=point
            )
            
            print(f"✅ Logged temperature: {temperature}°C")
            time.sleep(1)  # Separate points by 1 second
        
        print("Complete. Return to the InfluxDB UI.")
        return True

# Usage
if __name__ == "__main__":
    try:
        logger = TuyaTemperatureLogger()
        logger.log_temperature_to_influxdb()
    except Exception as e:
        print(f"❌ Error: {e}")