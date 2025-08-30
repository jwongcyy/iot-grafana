import requests
import json
import time
import hashlib
import hmac
import os
import urllib.parse
import csv
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables from .env file
load_dotenv()

class TuyaCloudAPI:
    def __init__(self):
        self.client_id = os.getenv('TUYA_ACCESS_ID')
        self.secret = os.getenv('TUYA_ACCESS_SECRET')
        self.region = os.getenv('REGION', 'tuyaus').lower()
        self.base_url = os.getenv('TUYA_BASE_URL', self._get_base_url_from_region())
        self.access_token = None
        self.token_expire_time = 0
        self.csv_file = os.getenv('CSV_FILE', 'tuya/device.csv')
        
        # Validate required environment variables
        if not self.client_id or not self.secret:
            raise ValueError("TUYA_ACCESS_ID and TUYA_ACCESS_SECRET must be set in .env file")
        
        print(f"Initialized with Client ID: {self.client_id}")
        print(f"Base URL: {self.base_url}")
        print(f"CSV File: {self.csv_file}")
        
        # Initialize CSV file with headers if it doesn't exist
        self._initialize_csv()
        
    def _initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['DateTime', 'Temperature'])
            print(f"Created new CSV file: {self.csv_file}")
    
    def _append_to_csv(self, datetime_str: str, temperature: float):
        """Append data to CSV file"""
        try:
            with open(self.csv_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([datetime_str, temperature])
            print(f"✅ Data appended to CSV: {datetime_str}, {temperature}°C")
        except Exception as e:
            print(f"❌ Error writing to CSV: {e}")
    
    def _get_base_url_from_region(self) -> str:
        """Get base URL based on region"""
        region_urls = {
            'tuyacn': 'https://openapi.tuyacn.com',
            'tuyaus': 'https://openapi.tuyaus.com',
            'tuyaeu': 'https://openapi.tuyaeu.com',
            'tuyain': 'https://openapi.tuyain.com'
        }
        return region_urls.get(self.region, 'https://openapi.tuyaus.com')
    
    def _string_to_sign(self, query_params: Dict[str, str] = None, body: str = "", method: str = "GET", path: str = "") -> Dict[str, str]:
        """
        Generate the string to sign according to Tuya's algorithm
        """
        # Process query parameters
        arr = []
        param_map = {}
        url_path = path
        
        if query_params:
            for key, value in query_params.items():
                arr.append(key)
                param_map[key] = value
        
        # Sort parameters alphabetically
        arr.sort()
        
        # Build URL with query parameters
        if arr:
            query_str = "&".join([f"{key}={urllib.parse.quote(str(param_map[key]))}" for key in arr])
            url_path = f"{path}?{query_str}"
        else:
            url_path = path
        
        # Calculate SHA256 of body
        if body:
            body_sha256 = hashlib.sha256(body.encode('utf-8')).hexdigest()
        else:
            body_sha256 = hashlib.sha256(b'').hexdigest()
        
        # For device API calls, we don't use Signature-Headers, so headers_str is empty
        headers_str = ""
        
        # Build the sign URL string
        sign_url = f"{method}\n{body_sha256}\n{headers_str}\n{url_path}"
        
        return {
            "signUrl": sign_url,
            "url": url_path
        }
    
    def _calc_sign(self, client_id: str, access_token: str, timestamp: str, nonce: str, sign_str: str, secret: str) -> str:
        """
        Calculate the HMAC-SHA256 signature
        """
        # Build the string to sign
        str_to_sign = client_id + access_token + timestamp + nonce + sign_str
        
        # Calculate HMAC-SHA256
        signature = hmac.new(
            secret.encode('utf-8'),
            str_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        
        return signature
    
    def get_access_token(self) -> str:
        """Get access token from Tuya Cloud"""
        if self.access_token and time.time() < self.token_expire_time:
            return self.access_token
            
        # For token endpoint, we need to include grant_type parameter
        query_params = {
            'grant_type': '1'
        }
        
        endpoint = "/v1.0/token"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for token request
        
        # Generate string to sign with query parameters
        sign_map = self._string_to_sign(query_params=query_params, method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature (no access token for token request)
        access_token_for_sign = ""
        sign = self._calc_sign(self.client_id, access_token_for_sign, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        # Build URL with query parameters
        request_url = f"{full_url}?grant_type=1"
        
        try:
            print(f"Getting access token from: {request_url}")
            print(f"Timestamp: {timestamp}")
            print(f"String to sign: {repr(sign_str)}")
            print(f"Signature: {sign}")
            
            response = requests.get(request_url, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            print(f"Token response: {json.dumps(result, indent=2)}")
            
            if result['success']:
                self.access_token = result['result']['access_token']
                self.token_expire_time = time.time() + result['result']['expire_time'] - 300
                print(f"Access token obtained successfully: {self.access_token[:20]}...")
                return self.access_token
            else:
                raise Exception(f"Failed to get access token: {result.get('msg', 'Unknown error')}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
    
    def get_device_info(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        GET {{url}}/v1.0/devices/{{device_id}}
        Get detailed device information
        """
        # Use device_id from parameter or environment variable
        target_device_id = device_id or os.getenv('TUYA_DEVICE_ID')
        if not target_device_id:
            raise ValueError("Device ID must be provided either as parameter or in TUYA_DEVICE_ID environment variable")
        
        access_token = self.get_access_token()
        endpoint = f"/v1.0/devices/{target_device_id}"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for device API
        body = ""   # Empty body for GET request
        
        # Generate string to sign
        sign_map = self._string_to_sign(method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature
        sign = self._calc_sign(self.client_id, access_token, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'access_token': access_token,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        print(f"\nGetting device info from: {full_url}")
        print(f"Timestamp: {timestamp}")
        print(f"String to sign: {repr(sign_str)}")
        print(f"Signature: {sign}")
        print(f"Access Token: {access_token[:20]}...")
        
        try:
            response = requests.get(full_url, headers=headers, timeout=10)
            print(f"Response status: {response.status_code}")
            
            result = response.json()
            print(f"Device info response: {json.dumps(result, indent=2)}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get device info: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")
    
    def get_device_status(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        GET {{url}}/v1.0/devices/{{device_id}}/status
        Get device status and append to CSV
        """
        target_device_id = device_id or os.getenv('TUYA_DEVICE_ID')
        if not target_device_id:
            raise ValueError("Device ID must be provided")
        
        access_token = self.get_access_token()
        endpoint = f"/v1.0/devices/{target_device_id}/status"
        full_url = f"{self.base_url}{endpoint}"
        timestamp = str(int(time.time() * 1000))
        method = "GET"
        nonce = ""  # Empty nonce for device API
        body = ""   # Empty body for GET request
        
        # Generate string to sign
        sign_map = self._string_to_sign(method=method, path=endpoint)
        sign_str = sign_map["signUrl"]
        
        # Calculate signature
        sign = self._calc_sign(self.client_id, access_token, timestamp, nonce, sign_str, self.secret)
        
        headers = {
            'client_id': self.client_id,
            'access_token': access_token,
            'sign': sign,
            't': timestamp,
            'sign_method': 'HMAC-SHA256',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(full_url, headers=headers, timeout=10)
            result = response.json()
            
            # Extract temperature data and append to CSV
            if result.get('success') and result.get('result'):
                current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y/%m/%d %H:%M')
                
                # Look for temperature in the status data
                for status_item in result['result']:
                    if status_item.get('code') == 'temp_current':  # Common temperature code
                        temperature = status_item.get('value') / 10.0
                        self._append_to_csv(current_time, temperature)
                        break
                else:
                    print("❌ Temperature data not found in device status")
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get device status: {e}")

# Usage example
if __name__ == "__main__":
    try:
        print("Testing Tuya Cloud API...")
        
        # Try the main method first
        print("Trying main method with query parameters...")
        tuya_api = TuyaCloudAPI()
        device_id = os.getenv('TUYA_DEVICE_ID')
        
        if not device_id:
            print("ERROR: TUYA_DEVICE_ID not found in environment variables")
        else:
            print(f"Device ID: {device_id}")
            
            # Get device status (which will also append to CSV)
            device_status = tuya_api.get_device_status(device_id)
            
            if device_status.get('success'):
                print("✅ SUCCESS: Device status retrieved and data appended to CSV!")
                print(f"Status response: {json.dumps(device_status, indent=2)}")
            else:
                print(f"❌ ERROR: {device_status.get('msg', 'Unknown error')}")
                print(f"Error Code: {device_status.get('code', 'N/A')}")
                
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
